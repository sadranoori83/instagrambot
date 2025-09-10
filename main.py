# -*- coding: utf-8 -*-
"""
InstaScheduler – Kivy Android app for scheduling Instagram posts and story reminders.
This version adds:
- File picker from phone storage.
- Dialog to choose between Post and Story.
- Story option triggers a reminder notification at the chosen time instead of posting automatically (because API does not support direct story posting).
"""

import os
import json
import time
import requests
from datetime import datetime, timezone
from dateutil import parser as dtparser
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from zoneinfo import ZoneInfo
from kivy.app import App
from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.clock import Clock
from plyer import notification

KV = r"""
#:set PAD 12

<RootUI@BoxLayout>:
    orientation: 'vertical'
    TabbedPanel:
        do_default_tab: False
        TabbedPanelItem:
            text: 'Schedule'
            BoxLayout:
                orientation: 'vertical'
                padding: PAD
                spacing: PAD
                TextInput:
                    id: caption
                    hint_text: 'Caption (optional)'
                    multiline: True
                TextInput:
                    id: datetime_input
                    hint_text: 'Publish time (YYYY-MM-DD HH:MM)'
                BoxLayout:
                    size_hint_y: None
                    height: 44
                    spacing: PAD
                    TextInput:
                        id: local_path
                        hint_text: 'Local media file path'
                    Button:
                        text: 'Pick File'
                        size_hint_x: 0.3
                        on_release: app.pick_file()
                BoxLayout:
                    size_hint_y: None
                    height: 44
                    spacing: PAD
                    Button:
                        text: 'Schedule'
                        on_release: app.choose_type_and_schedule()
                    Button:
                        text: 'Clear'
                        on_release: app.clear_form()
                Label:
                    id: status_label
                    text: app.status_text
                    color: (0.9,0.9,0.9,1)
                    size_hint_y: None
                    height: self.texture_size[1] + 8
        TabbedPanelItem:
            text: 'Settings'
            BoxLayout:
                orientation: 'vertical'
                padding: PAD
                spacing: PAD
                TextInput:
                    id: ig_id
                    hint_text: 'Instagram Business ID'
                    text: app.ig_business_id
                TextInput:
                    id: access_token
                    hint_text: 'Access Token'
                    text: app.access_token
                    password: True
                BoxLayout:
                    size_hint_y: None
                    height: 44
                    spacing: PAD
                    Button:
                        text: 'Save'
                        on_release: app.save_settings(ig_id.text, access_token.text)
"""

SETTINGS_FILE = 'insta_settings.json'
SCHEDULE_FILE = 'insta_schedule.json'
API_BASE = 'https://graph.facebook.com/v19.0'


def load_json(path, default):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


class InstaClient:
    def __init__(self, ig_id, token, logger):
        self.ig_id = ig_id
        self.token = token
        self.logger = logger

    def create_media_container(self, url, caption, is_video):
        endpoint = f"{API_BASE}/{self.ig_id}/media"
        data = {
            'access_token': self.token,
            'caption': caption or ''
        }
        if is_video:
            data.update({'media_type': 'VIDEO', 'video_url': url})
        else:
            data.update({'image_url': url})
        r = requests.post(endpoint, data=data, timeout=60)
        r.raise_for_status()
        return r.json().get('id')

    def publish_media(self, container_id):
        endpoint = f"{API_BASE}/{self.ig_id}/media_publish"
        r = requests.post(endpoint, data={'creation_id': container_id, 'access_token': self.token})
        r.raise_for_status()
        return r.json()


class InstaSchedulerApp(App):
    status_text = StringProperty('Ready.')
    access_token = StringProperty('')
    ig_business_id = StringProperty('')

    def build(self):
        self.icon = None
        self._jobs = {}
        self.settings = load_json(SETTINGS_FILE, {'ig_business_id': '', 'access_token': ''})
        self.ig_business_id = self.settings.get('ig_business_id', '')
        self.access_token = self.settings.get('access_token', '')
        executors = {'default': ThreadPoolExecutor(4)}
        self.scheduler = BackgroundScheduler(executors=executors, timezone=ZoneInfo("Asia/Tehran"))
        self.scheduler.start()
        return Builder.load_string(KV)

    def _log(self, msg):
        print(msg)
        self.status_text = msg

    def save_settings(self, ig_id, token):
        self.ig_business_id = ig_id.strip()
        self.access_token = token.strip()
        save_json(SETTINGS_FILE, {'ig_business_id': self.ig_business_id, 'access_token': self.access_token})
        self._log('Settings saved.')

    def clear_form(self):
        ids = self.root.ids
        ids.caption.text = ''
        ids.datetime_input.text = ''
        ids.local_path.text = ''
        self._log('Form cleared.')

    def pick_file(self):
        from kivy.uix.filechooser import FileChooserIconView
        layout = BoxLayout(orientation='vertical')
        chooser = FileChooserIconView(filters=['*.jpg','*.jpeg','*.png','*.mp4','*.mov'])
        btn = Button(text='Select', size_hint_y=None, height=44)
        popup = Popup(title='Pick Media', content=layout, size_hint=(0.95,0.95))
        def select_and_close(_):
            sel = chooser.selection
            if sel:
                self.root.ids.local_path.text = sel[0]
            popup.dismiss()
        btn.bind(on_release=select_and_close)
        layout.add_widget(chooser)
        layout.add_widget(btn)
        popup.open()

    def choose_type_and_schedule(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        btn_post = Button(text='پست', size_hint_y=None, height=44)
        btn_story = Button(text='استوری', size_hint_y=None, height=44)
        popup = Popup(title='انتخاب نوع انتشار', content=layout, size_hint=(0.8,0.4))
        layout.add_widget(btn_post)
        layout.add_widget(btn_story)

        def choose_post(_):
            popup.dismiss()
            self.schedule_post('post')
        def choose_story(_):
            popup.dismiss()
            self.schedule_post('story')
        btn_post.bind(on_release=choose_post)
        btn_story.bind(on_release=choose_story)
        popup.open()

    def schedule_post(self, post_type):
        ids = self.root.ids
        caption = ids.caption.text.strip()
        when_text = ids.datetime_input.text.strip()
        path = ids.local_path.text.strip()
        if not path or not os.path.exists(path):
            self._log('Please choose a valid file.')
            return
        if not when_text:
            self._log('Enter a valid time.')
            return
        try:
            when = dtparser.parse(when_text)
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc).astimezone()
        except Exception:
            self._log('Invalid time format.')
            return

        job_id = f"job-{int(time.time()*1000)}"
        if post_type == 'post':
            self.scheduler.add_job(self._do_post_job, 'date', run_date=when, args=[path, caption], id=job_id)
            self._log(f'Scheduled a POST at {when}')
        else:
            self.scheduler.add_job(self._story_reminder, 'date', run_date=when, args=[path], id=job_id)
            self._log(f'Scheduled a STORY reminder at {when}')

    def _do_post_job(self, path, caption):
        self._log(f'Would upload and post: {path}')
        # You need to implement upload logic here to get a public URL and then call InstaClient
        notification.notify(title='Instagram Post', message=f'Posting {os.path.basename(path)}')

    def _story_reminder(self, path):
        self._log(f'Reminder for Story: {path}')
        notification.notify(title='Instagram Story Reminder', message=f'Open Instagram to post story: {os.path.basename(path)}')


if __name__ == '__main__':
    InstaSchedulerApp().run()
