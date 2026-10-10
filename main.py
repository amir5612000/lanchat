# main.py - LANChat Android with Persian Font & RTL
import os
import sys
import json
import time
import socket
import struct
import threading
from datetime import datetime

from kivy.app import App
from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.utils import platform

# ==================== ثبت فونت فارسی ====================
from fonts_setup import register_fonts, fa
FONT_NAME = register_fonts()

# ==================== مسیرها ====================
def get_app_dir():
    if platform == 'android':
        try:
            from android.storage import app_storage_path
            return app_storage_path()
        except:
            return os.path.expanduser('~')
    return os.path.expanduser('~')

APP_DIR     = get_app_dir()
CONFIG_PATH = os.path.join(APP_DIR, '.lanchat_config.json')
HISTORY_DIR = os.path.join(APP_DIR, '.lanchat_history')
PENDING_DIR = os.path.join(APP_DIR, '.lanchat_pending')
GROUPS_DIR  = os.path.join(APP_DIR, '.lanchat_groups')

for _d in [HISTORY_DIR, PENDING_DIR, GROUPS_DIR]:
    os.makedirs(_d, exist_ok=True)

# ==================== رنگ‌ها ====================
COLORS = {
    'bg_dark':   '#1a1a2e', 'bg_medium': '#16213e', 'bg_light': '#0f3460',
    'accent':    '#e94560', 'accent2':   '#533483',
    'text':      '#eaeaea', 'text_dim':  '#a0a0b0',
    'online':    '#4ecca3', 'away':      '#f5a623',
    'busy':      '#e94560', 'offline':   '#666680',
    'msg_sent':  '#1e3a5f', 'msg_recv':  '#2d1b4e',
    'link':      '#4fc3f7', 'deleted':   '#555566',
    'pending':   '#7a6000', 'group':     '#2d4b3e',
    'group_accent': '#4ecdc4',
}

PORTS = {'discovery': 55000, 'message': 55001, 'file': 55002, 'group': 55003}
STATUS_LIST = ['آنلاین', 'مشغول', 'دور']
STATUS_COLORS = {
    'آنلاین': COLORS['online'], 'مشغول': COLORS['busy'], 'دور': COLORS['away']
}
EMOJIS = ['😀','😂','😍','😎','😭','😡','👍','👎','❤️','🔥','💯','🎉','🙏','💀','😴','🤔','😱','🥳']

# ==================== صدا ====================
def play_sound(sound_type='msg'):
    def _play():
        try:
            if platform == 'android':
                from jnius import autoclass
                ToneGenerator = autoclass('android.media.ToneGenerator')
                AudioManager = autoclass('android.media.AudioManager')
                tone_map = {
                    'msg':     ToneGenerator.TONE_PROP_BEEP,
                    'sent':    ToneGenerator.TONE_PROP_ACK,
                    'buzz':    ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD,
                    'file':    ToneGenerator.TONE_PROP_BEEP2,
                    'pending': ToneGenerator.TONE_PROP_PROMPT,
                    'group':   ToneGenerator.TONE_PROP_BEEP,
                }
                tone = tone_map.get(sound_type, ToneGenerator.TONE_PROP_BEEP)
                tg = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)
                tg.startTone(tone, 200)
                time.sleep(0.5)
                tg.release()
            else:
                try:
                    import winsound
                    winsound.Beep(880, 120)
                except:
                    pass
        except Exception as e:
            print(f'sound error: {e}')
    threading.Thread(target=_play, daemon=True).start()

# ==================== Config ====================
def load_config():
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_config(data: dict):
    try:
        cfg = load_config()
        cfg.update(data)
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'save_config error: {e}')

# ==================== تاریخچه ====================
def _history_path(my_user, peer):
    key = '__'.join(sorted([my_user, peer]))
    return os.path.join(HISTORY_DIR, f'{key}.json')

def load_history(my_user, peer):
    try:
        with open(_history_path(my_user, peer), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_history(my_user, peer, msgs):
    try:
        with open(_history_path(my_user, peer), 'w', encoding='utf-8') as f:
            json.dump(msgs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f'save_history error: {e}')

def append_history(my_user, peer, entry):
    msgs = load_history(my_user, peer)
    msgs.append(entry)
    save_history(my_user, peer, msgs)

# ==================== تاریخچه گروهی ====================
def _group_history_path(g):
    return os.path.join(GROUPS_DIR, f'{g}.json')

def load_group_history(g):
    try:
        with open(_group_history_path(g), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_group_history(g, msgs):
    try:
        with open(_group_history_path(g), 'w', encoding='utf-8') as f:
            json.dump(msgs, f, ensure_ascii=False, indent=2)
    except: pass

def append_group_history(g, entry):
    msgs = load_group_history(g)
    msgs.append(entry)
    save_group_history(g, msgs)

def delete_group_history(g):
    try:
        p = _group_history_path(g)
        if os.path.exists(p):
            os.remove(p)
            return True
    except: pass
    return False

# ==================== Pending ====================
def _pending_path(my_user, peer):
    return os.path.join(PENDING_DIR, f'{my_user}_to_{peer}.json')

def load_pending(my_user, peer):
    try:
        with open(_pending_path(my_user, peer), 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_pending(my_user, peer, msgs):
    try:
        with open(_pending_path(my_user, peer), 'w', encoding='utf-8') as f:
            json.dump(msgs, f, ensure_ascii=False, indent=2)
    except: pass

def add_pending(my_user, peer, entry):
    msgs = load_pending(my_user, peer)
    msgs.append(entry)
    save_pending(my_user, peer, msgs)

def clear_pending(my_user, peer):
    try:
        os.remove(_pending_path(my_user, peer))
    except: pass

# ==================== نوتیفیکیشن ====================
def send_notification(title, message):
    if platform != 'android':
        print(f'[NOTIFY] {title}: {message}')
        return
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')
        NotificationBuilder = autoclass('android.app.Notification$Builder')
        NotificationManager = autoclass('android.app.NotificationManager')

        activity = PythonActivity.mActivity
        channel_id = "lanchat_channel"
        try:
            NotificationChannel = autoclass('android.app.NotificationChannel')
            nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
            chan = NotificationChannel(channel_id, "LANChat",
                                        NotificationManager.IMPORTANCE_HIGH)
            nm.createNotificationChannel(chan)
        except: pass

        intent = Intent(activity, PythonActivity)
        pi = PendingIntent.getActivity(activity, 0, intent,
                                        PendingIntent.FLAG_UPDATE_CURRENT)
        builder = NotificationBuilder(activity, channel_id)
        builder.setContentTitle(title)
        builder.setContentText(message)
        builder.setSmallIcon(activity.getApplicationInfo().icon)
        builder.setContentIntent(pi)
        builder.setAutoCancel(True)
        nm = activity.getSystemService(Context.NOTIFICATION_SERVICE)
        nm.notify(int(time.time()) % 100000, builder.build())
    except Exception as e:
        print(f'notification error: {e}')

# ==================== NetworkManager ====================
class NetworkManager:
    def __init__(self, app):
        self.app = app
        self.username = ''
        self.running = False
        self.peers = {}
        self.groups = {}

    def start(self, username):
        self.username = username
        self.running = True
        for target in [self._discovery_listener, self._message_listener,
                       self._file_listener, self._group_listener,
                       self._broadcast_loop, self._cleanup_loop]:
            threading.Thread(target=target, daemon=True).start()

    def stop(self):
        self.running = False
        self._send_broadcast('LEAVE')

    def _get_broadcast_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return '.'.join(ip.split('.')[:3]) + '.255'
        except:
            return '255.255.255.255'

    def _send_broadcast(self, msg_type):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            data = json.dumps({
                'type': msg_type, 'username': self.username,
                'status': self.app.current_status
            }).encode('utf-8')
            sock.sendto(data, (self._get_broadcast_ip(), PORTS['discovery']))
            sock.close()
        except: pass

    def _broadcast_loop(self):
        while self.running:
            self._send_broadcast('HELLO')
            time.sleep(5)

    def _cleanup_loop(self):
        while self.running:
            now = time.time()
            to_remove = [ip for ip, p in list(self.peers.items())
                         if now - p['last_seen'] > 15]
            for ip in to_remove:
                uname = self.peers[ip]['username']
                del self.peers[ip]
                Clock.schedule_once(
                    lambda dt, ip=ip, u=uname: self.app.remove_peer(ip, u), 0)
            time.sleep(5)

    def _discovery_listener(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', PORTS['discovery']))
            sock.settimeout(1)
        except Exception as e:
            print(f'discovery bind error: {e}')
            return
        while self.running:
            try:
                data, addr = sock.recvfrom(1024)
                ip = addr[0]
                info = json.loads(data.decode('utf-8'))
                if info['username'] == self.username:
                    continue
                if info['type'] == 'LEAVE':
                    if ip in self.peers:
                        uname = self.peers[ip]['username']
                        del self.peers[ip]
                        Clock.schedule_once(
                            lambda dt, ip=ip, u=uname: self.app.remove_peer(ip, u), 0)
                else:
                    old = self.peers.get(ip)
                    just_came_online = (old is None)
                    self.peers[ip] = {
                        'username': info['username'],
                        'status': info['status'],
                        'last_seen': time.time()
                    }
                    Clock.schedule_once(lambda dt, ip=ip, i=info, o=old:
                        self.app.update_peer(ip, i['username'], i['status'], o), 0)
                    if just_came_online:
                        Clock.schedule_once(lambda dt, ip=ip, u=info['username']:
                            self.app.flush_pending(ip, u), 0.2)
            except: pass
        sock.close()

    def _message_listener(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', PORTS['message']))
            sock.listen(10)
            sock.settimeout(1)
        except Exception as e:
            print(f'message bind error: {e}')
            return
        while self.running:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_message,
                                 args=(conn, addr[0]), daemon=True).start()
            except: pass
        sock.close()

    def _handle_message(self, conn, ip):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                data += chunk
            msg = json.loads(data.decode('utf-8'))
            Clock.schedule_once(lambda dt: self.app.receive_message(ip, msg), 0)
        except: pass
        finally: conn.close()

    def send_message(self, ip, msg_type, content, peer_username='',
                     save_to_history=True, msg_id=None):
        if msg_id is None:
            msg_id = f'{time.time():.6f}'

        def _send():
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((ip, PORTS['message']))
                data = json.dumps({
                    'type': msg_type, 'content': content,
                    'username': self.username, 'msg_id': msg_id,
                }).encode('utf-8')
                sock.sendall(data)
                sock.close()
                if save_to_history and msg_type == 'MSG' and peer_username:
                    entry = {
                        'id': msg_id, 'direction': 'sent', 'content': content,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'deleted': False,
                    }
                    append_history(self.username, peer_username, entry)
            except Exception:
                if msg_type == 'MSG' and peer_username:
                    entry = {
                        'id': msg_id, 'direction': 'sent', 'content': content,
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'deleted': False, 'pending': True,
                    }
                    add_pending(self.username, peer_username, entry)
                    append_history(self.username, peer_username, entry)
                    Clock.schedule_once(
                        lambda dt: self.app.mark_message_pending(ip, msg_id), 0)

        threading.Thread(target=_send, daemon=True).start()

    def _file_listener(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', PORTS['file']))
            sock.listen(5)
            sock.settimeout(1)
        except Exception as e:
            print(f'file bind error: {e}')
            return
        while self.running:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_file,
                                 args=(conn, addr[0]), daemon=True).start()
            except: pass
        sock.close()

    def _handle_file(self, conn, ip):
        try:
            header_len = struct.unpack('!I', conn.recv(4))[0]
            header = json.loads(conn.recv(header_len).decode('utf-8'))
            filename = header['filename']
            filesize = header['filesize']
            if platform == 'android':
                try:
                    from android.storage import primary_external_storage_path
                    dl = os.path.join(primary_external_storage_path(), 'Download')
                except:
                    dl = os.path.join(os.path.expanduser('~'), 'Downloads')
            else:
                dl = os.path.join(os.path.expanduser('~'), 'Downloads')
            os.makedirs(dl, exist_ok=True)
            save_path = os.path.join(dl, filename)
            received = 0
            with open(save_path, 'wb') as f:
                while received < filesize:
                    chunk = conn.recv(min(65536, filesize - received))
                    if not chunk: break
                    f.write(chunk)
                    received += len(chunk)
            Clock.schedule_once(
                lambda dt: self.app.receive_file_notification(ip, filename, save_path), 0)
        except Exception as e:
            print('file recv error:', e)
        finally: conn.close()

    def send_file(self, ip, filepath, peer_username=''):
        def _send():
            try:
                filename = os.path.basename(filepath)
                filesize = os.path.getsize(filepath)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(30)
                sock.connect((ip, PORTS['file']))
                header = json.dumps({'filename': filename, 'filesize': filesize}).encode('utf-8')
                sock.sendall(struct.pack('!I', len(header)))
                sock.sendall(header)
                with open(filepath, 'rb') as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk: break
                        sock.sendall(chunk)
                sock.close()
                Clock.schedule_once(
                    lambda dt: self.app.file_sent_notification(ip, filename), 0)
                if peer_username:
                    entry = {
                        'id': f'{time.time():.6f}', 'direction': 'sent',
                        'content': f'[فایل] {filename}',
                        'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'deleted': False, 'file_path': filepath,
                    }
                    append_history(self.username, peer_username, entry)
            except Exception as e:
                print(f'send_file error: {e}')
        threading.Thread(target=_send, daemon=True).start()

    def update_status(self, new_status):
        self.app.current_status = new_status
        self._send_broadcast('HELLO')

    # ============ گروه‌ها ============
    def _group_listener(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', PORTS['group']))
            sock.listen(10)
            sock.settimeout(1)
        except Exception as e:
            print(f'group bind error: {e}')
            return
        while self.running:
            try:
                conn, addr = sock.accept()
                threading.Thread(target=self._handle_group_message,
                                 args=(conn, addr[0]), daemon=True).start()
            except: pass
        sock.close()

    def _handle_group_message(self, conn, ip):
        try:
            data = b''
            while True:
                chunk = conn.recv(4096)
                if not chunk: break
                data += chunk
            msg = json.loads(data.decode('utf-8'))
            Clock.schedule_once(
                lambda dt: self.app.receive_group_message(ip, msg), 0)
        except: pass
        finally: conn.close()

    def send_group_message(self, group_name, content, members):
        msg_id = f'{time.time():.6f}'

        def _send_to(peer_ip):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                sock.connect((peer_ip, PORTS['group']))
                data = json.dumps({
                    'type': 'GROUP_MSG', 'group_name': group_name,
                    'content': content, 'username': self.username,
                    'msg_id': msg_id,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }).encode('utf-8')
                sock.sendall(data)
                sock.close()
                return True
            except:
                return False

        for ip, username in members:
            if username == self.username: continue
            peer_ip = None
            for p_ip, info in self.peers.items():
                if info['username'] == username:
                    peer_ip = p_ip
                    break
            if peer_ip:
                _send_to(peer_ip)

        entry = {
            'id': msg_id, 'username': self.username, 'content': content,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'deleted': False
        }
        append_group_history(group_name, entry)
        Clock.schedule_once(
            lambda dt: self.app.add_group_message(group_name, entry), 0)

    def create_group(self, group_name, members):
        if group_name in self.groups:
            return False, 'گروه با این نام وجود دارد'
        self.groups[group_name] = {
            'members': members, 'creator': self.username,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        groups_data = load_config().get('groups', {})
        groups_data[group_name] = self.groups[group_name]
        save_config({'groups': groups_data})
        return True, 'گروه ایجاد شد'

    def get_groups(self):
        self.groups = load_config().get('groups', {})
        return self.groups

    def leave_group(self, group_name):
        if group_name in self.groups:
            members = self.groups[group_name]['members']
            if self.username in members:
                members.remove(self.username)
                groups_data = load_config().get('groups', {})
                if not members:
                    del self.groups[group_name]
                    groups_data.pop(group_name, None)
                    delete_group_history(group_name)
                else:
                    self.groups[group_name]['members'] = members
                    groups_data[group_name]['members'] = members
                save_config({'groups': groups_data})
                return True
        return False

    def delete_group(self, group_name):
        if group_name not in self.groups:
            return False, 'گروه وجود ندارد'
        if self.groups[group_name]['creator'] != self.username:
            return False, 'فقط سازنده می‌تواند حذف کند'
        del self.groups[group_name]
        groups_data = load_config().get('groups', {})
        groups_data.pop(group_name, None)
        save_config({'groups': groups_data})
        delete_group_history(group_name)
        return True, 'گروه حذف شد'

    def rename_group(self, old_name, new_name):
        if old_name not in self.groups:
            return False, 'گروه وجود ندارد'
        if self.groups[old_name]['creator'] != self.username:
            return False, 'فقط سازنده می‌تواند نام را تغییر دهد'
        if new_name in self.groups:
            return False, 'گروه با این نام وجود دارد'
        self.groups[new_name] = self.groups[old_name].copy()
        del self.groups[old_name]
        groups_data = load_config().get('groups', {})
        groups_data[new_name] = groups_data[old_name].copy()
        del groups_data[old_name]
        save_config({'groups': groups_data})
        try:
            if os.path.exists(_group_history_path(old_name)):
                os.rename(_group_history_path(old_name),
                          _group_history_path(new_name))
        except: pass
        return True, f'نام گروه به "{new_name}" تغییر یافت'

    def add_member_to_group(self, group_name, new_member):
        if group_name not in self.groups:
            return False, 'گروه وجود ندارد'
        if new_member in self.groups[group_name]['members']:
            return False, 'این کاربر قبلاً عضو است'
        self.groups[group_name]['members'].append(new_member)
        groups_data = load_config().get('groups', {})
        if group_name in groups_data:
            groups_data[group_name]['members'] = self.groups[group_name]['members']
            save_config({'groups': groups_data})
        return True, f'{new_member} اضافه شد'

    def remove_member_from_group(self, group_name, member):
        if group_name not in self.groups:
            return False, 'گروه وجود ندارد'
        if member == self.groups[group_name]['creator']:
            return False, 'نمی‌توان سازنده را حذف کرد'
        if member not in self.groups[group_name]['members']:
            return False, 'این کاربر عضو نیست'
        self.groups[group_name]['members'].remove(member)
        groups_data = load_config().get('groups', {})
        if group_name in groups_data:
            groups_data[group_name]['members'] = self.groups[group_name]['members']
            save_config({'groups': groups_data})
        return True, f'{member} حذف شد'


# ==================== KV Layout ====================
KV = f'''
<Label>:
    font_name: '{FONT_NAME}'

<Button>:
    font_name: '{FONT_NAME}'

<TextInput>:
    font_name: '{FONT_NAME}'

<LoginScreen>:
    BoxLayout:
        orientation: 'vertical'
        padding: dp(30)
        spacing: dp(15)
        canvas.before:
            Color:
                rgba: app.hex_to_rgba(app.colors['bg_dark'])
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: app.fa_text('💬 LAN Chat')
            font_size: '28sp'
            bold: True
            color: app.hex_to_rgba(app.colors['accent'])
            size_hint_y: None
            height: dp(50)
        Label:
            text: app.fa_text('چت شبکه محلی - اندروید')
            font_size: '14sp'
            color: app.hex_to_rgba(app.colors['text_dim'])
            size_hint_y: None
            height: dp(30)
        Widget:
            size_hint_y: None
            height: dp(20)
        Label:
            text: app.fa_text('نام کاربری:')
            font_size: '15sp'
            color: app.hex_to_rgba(app.colors['text'])
            size_hint_y: None
            height: dp(30)
            halign: 'right'
            text_size: self.width, None
        TextInput:
            id: username_input
            multiline: False
            font_size: '16sp'
            size_hint_y: None
            height: dp(50)
            background_color: app.hex_to_rgba(app.colors['bg_medium'])
            foreground_color: app.hex_to_rgba(app.colors['text'])
            cursor_color: app.hex_to_rgba(app.colors['text'])
            halign: 'right'
        Label:
            text: app.fa_text('وضعیت:')
            font_size: '15sp'
            color: app.hex_to_rgba(app.colors['text'])
            size_hint_y: None
            height: dp(30)
            halign: 'right'
            text_size: self.width, None
        BoxLayout:
            size_hint_y: None
            height: dp(45)
            spacing: dp(10)
            ToggleButton:
                id: st_online
                text: app.fa_text('آنلاین')
                group: 'status'
                state: 'down'
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['online'])
            ToggleButton:
                id: st_busy
                text: app.fa_text('مشغول')
                group: 'status'
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['busy'])
            ToggleButton:
                id: st_away
                text: app.fa_text('دور')
                group: 'status'
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['away'])
        Widget:
            size_hint_y: None
            height: dp(20)
        Button:
            text: app.fa_text('ورود به شبکه')
            font_size: '17sp'
            bold: True
            size_hint_y: None
            height: dp(55)
            background_normal: ''
            background_color: app.hex_to_rgba(app.colors['accent'])
            on_release: root.do_login()

<MainScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: app.hex_to_rgba(app.colors['bg_dark'])
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: app.hex_to_rgba(app.colors['bg_light'])
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: app.fa_text('💬 ' + app.username)
                font_size: '18sp'
                bold: True
                color: app.hex_to_rgba(app.colors['accent'])
            Button:
                text: app.fa_text('خروج')
                size_hint_x: None
                width: dp(80)
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['accent2'])
                on_release: root.do_logout()
        TextInput:
            id: search_input
            hint_text: app.fa_text('جستجوی کاربر...')
            multiline: False
            size_hint_y: None
            height: dp(45)
            font_size: '14sp'
            background_color: app.hex_to_rgba(app.colors['bg_medium'])
            foreground_color: app.hex_to_rgba(app.colors['text'])
            padding: dp(10), dp(10)
            halign: 'right'
            on_text: root.do_search(self.text)
        BoxLayout:
            size_hint_y: None
            height: dp(45)
            ToggleButton:
                id: tab_users
                text: app.fa_text('👤 کاربران')
                group: 'tabs'
                state: 'down'
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['bg_light'])
                on_release: root.switch_tab('users')
            ToggleButton:
                id: tab_groups
                text: app.fa_text('👥 گروه‌ها')
                group: 'tabs'
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['bg_light'])
                on_release: root.switch_tab('groups')
        ScrollView:
            BoxLayout:
                id: peer_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(3)
                padding: dp(5)
        BoxLayout:
            size_hint_y: None
            height: dp(55)
            padding: dp(5)
            spacing: dp(5)
            Button:
                text: app.fa_text('➕ گروه جدید')
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['accent2'])
                on_release: root.open_create_group()
            Button:
                text: app.fa_text('🔄 به‌روزرسانی')
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['bg_light'])
                on_release: root.rebuild_list()

<ChatScreen>:
    BoxLayout:
        orientation: 'vertical'
        canvas.before:
            Color:
                rgba: app.hex_to_rgba(app.colors['bg_dark'])
            Rectangle:
                pos: self.pos
                size: self.size
        BoxLayout:
            size_hint_y: None
            height: dp(60)
            padding: dp(10)
            canvas.before:
                Color:
                    rgba: app.hex_to_rgba(app.colors['bg_light'])
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '◀'
                size_hint_x: None
                width: dp(50)
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['bg_medium'])
                on_release: root.go_back()
            Label:
                id: chat_title
                text: root.chat_title_text
                font_size: '16sp'
                bold: True
                color: app.hex_to_rgba(app.colors['text'])
            Button:
                text: '📎'
                size_hint_x: None
                width: dp(50)
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['accent2'])
                on_release: root.pick_file()
        ScrollView:
            id: msg_scroll
            BoxLayout:
                id: msg_container
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(8)
                spacing: dp(5)
        BoxLayout:
            size_hint_y: None
            height: dp(55)
            padding: dp(5)
            spacing: dp(5)
            TextInput:
                id: msg_input
                hint_text: app.fa_text('پیام...')
                multiline: False
                background_color: app.hex_to_rgba(app.colors['bg_light'])
                foreground_color: app.hex_to_rgba(app.colors['text'])
                halign: 'right'
                on_text_validate: root.send_msg()
            Button:
                text: '▶'
                size_hint_x: None
                width: dp(60)
                background_normal: ''
                background_color: app.hex_to_rgba(app.colors['accent'])
                on_release: root.send_msg()
'''

Builder.load_string(KV)


# ==================== LoginScreen ====================
class LoginScreen(Screen):
    def do_login(self):
        name = self.ids.username_input.text.strip()
        if not name:
            self._toast('نام کاربری را وارد کنید')
            return
        if self.ids.st_busy.state == 'down':
            status = 'مشغول'
        elif self.ids.st_away.state == 'down':
            status = 'دور'
        else:
            status = 'آنلاین'

        app = App.get_running_app()
        app.username = name
        app.current_status = status
        save_config({'username': name, 'status': status, 'auto_login': True})
        app.go_main()

    def _toast(self, msg):
        popup = Popup(
            title=fa('خطا'),
            title_font=FONT_NAME,
            content=Label(text=fa(msg), font_name=FONT_NAME),
            size_hint=(0.8, 0.3))
        popup.open()


# ==================== MainScreen ====================
class MainScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_tab = 'users'
        self._refreshing = False
        Clock.schedule_once(lambda dt: self.rebuild_list(), 0.5)

    def refresh(self):
        self.rebuild_list()

    def switch_tab(self, tab):
        self.current_tab = tab
        self.rebuild_list()

    def do_search(self, text):
        self.rebuild_list()

    def rebuild_list(self):
        app = App.get_running_app()
        if not hasattr(self, 'ids') or 'peer_container' not in self.ids:
            Clock.schedule_once(lambda dt: self.rebuild_list(), 0.3)
            return

        container = self.ids.peer_container
        container.clear_widgets()

        query = ''
        try:
            query = self.ids.search_input.text.lower()
        except: pass

        if self.current_tab == 'users':
            for ip, info in app.network.peers.items():
                if query and query not in info['username'].lower():
                    continue
                self._add_peer_widget(container, ip, info)
        else:
            groups = app.network.get_groups()
            for name, data in groups.items():
                if app.username not in data['members']:
                    continue
                if query and query not in name.lower():
                    continue
                self._add_group_widget(container, name, data)

    def _add_peer_widget(self, container, ip, info):
        icon = {'آنلاین': '🟢', 'مشغول': '🔴', 'دور': '🟡'}.get(info['status'], '⚫')
        # ترتیب RTL: نام سپس وضعیت
        text_fa = fa(f'{info["username"]}  ({info["status"]})  {icon}')
        color = STATUS_COLORS.get(info['status'], COLORS['offline'])

        btn = Button(text=text_fa, font_size='15sp',
                     font_name=FONT_NAME,
                     size_hint_y=None, height=dp(55),
                     background_normal='',
                     background_color=App.get_running_app().hex_to_rgba(COLORS['bg_medium']),
                     color=App.get_running_app().hex_to_rgba(color),
                     halign='right')
        btn.bind(on_release=lambda x, k=ip: self._open_chat(k, False))
        container.add_widget(btn)

    def _add_group_widget(self, container, name, data):
        text_fa = fa(f'👥  {name}  ({len(data["members"])} عضو)')
        btn = Button(text=text_fa, font_size='15sp',
                     font_name=FONT_NAME,
                     size_hint_y=None, height=dp(55),
                     background_normal='',
                     background_color=App.get_running_app().hex_to_rgba(COLORS['bg_medium']),
                     color=App.get_running_app().hex_to_rgba(COLORS['group_accent']),
                     halign='right')
        btn.bind(on_release=lambda x, k=name: self._open_chat(k, True))
        container.add_widget(btn)

    def _open_chat(self, key, is_group):
        app = App.get_running_app()
        chat = app.root.get_screen('chat')
        chat.open_chat(key, is_group)
        app.root.current = 'chat'

    def open_create_group(self):
        app = App.get_running_app()
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))

        name_lbl = Label(text=fa('نام گروه:'),
                         size_hint_y=None, height=dp(30),
                         font_name=FONT_NAME,
                         halign='right', valign='middle')
        name_lbl.bind(size=name_lbl.setter('text_size'))
        content.add_widget(name_lbl)

        name_in = TextInput(hint_text=fa('نام گروه'), multiline=False,
                            font_name=FONT_NAME,
                            size_hint_y=None, height=dp(45),
                            halign='right')
        content.add_widget(name_in)

        members_lbl = Label(text=fa('اعضا:'),
                            size_hint_y=None, height=dp(30),
                            font_name=FONT_NAME,
                            halign='right', valign='middle')
        members_lbl.bind(size=members_lbl.setter('text_size'))
        content.add_widget(members_lbl)

        scroll = ScrollView()
        member_box = BoxLayout(orientation='vertical', size_hint_y=None, spacing=dp(5))
        member_box.bind(minimum_height=member_box.setter('height'))
        checkboxes = {}
        for ip, info in app.network.peers.items():
            if info['username'] == app.username:
                continue
            cb = ToggleButton(text=fa(info['username']),
                              font_name=FONT_NAME,
                              size_hint_y=None, height=dp(45))
            member_box.add_widget(cb)
            checkboxes[info['username']] = cb
        scroll.add_widget(member_box)
        content.add_widget(scroll)

        def create(_):
            gname = name_in.text.strip()
            if not gname:
                return
            members = [u for u, cb in checkboxes.items() if cb.state == 'down']
            members.append(app.username)
            ok, msg = app.network.create_group(gname, members)
            popup.dismiss()
            if ok:
                app.network.get_groups()
                self.rebuild_list()

        btn = Button(text=fa('ایجاد'), size_hint_y=None, height=dp(50),
                     font_name=FONT_NAME,
                     background_normal='',
                     background_color=app.hex_to_rgba(COLORS['accent']))
        btn.bind(on_release=create)
        content.add_widget(btn)

        popup = Popup(title=fa('ایجاد گروه'),
                      title_font=FONT_NAME,
                      content=content, size_hint=(0.9, 0.8))
        popup.open()

    def do_logout(self):
        app = App.get_running_app()
        save_config({'auto_login': False})
        app.network.stop()
        app.root.current = 'login'


# ==================== ChatScreen ====================
class ChatScreen(Screen):
    chat_username = StringProperty('')
    chat_ip = StringProperty('')
    chat_type = StringProperty('private')
    chat_title_text = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rendered_ids = set()
        self.chat_username = ''
        self.chat_ip = ''
        self.chat_type = 'private'
        self.chat_title_text = ''

    def go_back(self):
        self.root.current = 'main'

    def open_chat(self, key, is_group=False):
        app = App.get_running_app()
        self._rendered_ids = set()
        if 'msg_container' in self.ids:
            self.ids.msg_container.clear_widgets()

        if is_group:
            self.chat_type = 'group'
            self.chat_username = key
            self.chat_ip = ''
            self.chat_title_text = fa(f'👥 {key}')
            msgs = load_group_history(key)
            for m in msgs:
                self._render_history_group(m)
        else:
            self.chat_type = 'private'
            peer = app.network.peers.get(key)
            if not peer:
                return
            self.chat_username = peer['username']
            self.chat_ip = key
            self.chat_title_text = fa(f'💬 {peer["username"]}')
            msgs = load_history(app.username, peer['username'])
            for m in msgs:
                self._render_history_private(m)

    def _render_history_private(self, entry):
        self._render_bubble(
            entry.get('content', ''),
            is_sent=(entry.get('direction') == 'sent'),
            time_str=entry.get('time', '')[:16],
            pending=entry.get('pending', False))

    def _render_history_group(self, entry):
        app = App.get_running_app()
        is_sent = (entry.get('username', '') == app.username)
        name = entry.get('username', '')
        content = entry.get('content', '')
        # در RTL: نام سپس پیام
        text = content if is_sent else f'{name}: {content}'
        self._render_bubble(text, is_sent=is_sent,
                            time_str=entry.get('time', '')[:16])

    def _render_bubble(self, text, is_sent=True, time_str='', pending=False):
        if 'msg_container' not in self.ids:
            return

        bubble_box = BoxLayout(size_hint_y=None, padding=dp(5), spacing=dp(5))
        bubble_box.bind(minimum_height=bubble_box.setter('height'))

        prefix = '⏳ ' if pending else ''
        # RTL کردن متن
        display = fa(f'{prefix}{text}\n[{time_str}]')

        bubble = Label(
            text=display,
            font_size='14sp',
            font_name=FONT_NAME,
            color=App.get_running_app().hex_to_rgba(COLORS['text']),
            size_hint=(None, None),
            padding=(dp(12), dp(8)),
            halign='right',
            valign='middle',
            text_size=(dp(260), None))
        bubble.bind(texture_size=lambda inst, val: setattr(inst, 'size', val))

        if is_sent:
            bubble_box.add_widget(Label(size_hint_x=1))
            bubble_box.add_widget(bubble)
        else:
            bubble_box.add_widget(bubble)
            bubble_box.add_widget(Label(size_hint_x=1))

        self.ids.msg_container.add_widget(bubble_box)
        Clock.schedule_once(
            lambda dt: setattr(self.ids.msg_scroll, 'scroll_y', 0), 0.1)

    def send_msg(self):
        text = self.ids.msg_input.text.strip()
        if not text:
            return
        self.ids.msg_input.text = ''
        app = App.get_running_app()

        if self.chat_type == 'group':
            members_with_ip = []
            groups = app.network.get_groups()
            if self.chat_username in groups:
                members = groups[self.chat_username]['members']
                for ip, info in app.network.peers.items():
                    if info['username'] in members:
                        members_with_ip.append((ip, info['username']))
            members_with_ip.append(('localhost', app.username))
            app.network.send_group_message(self.chat_username, text, members_with_ip)
        else:
            if not self.chat_ip:
                return
            app.network.send_message(self.chat_ip, 'MSG', text,
                                     peer_username=self.chat_username)
            t = datetime.now().strftime('%H:%M')
            self._render_bubble(text, is_sent=True, time_str=t)
            play_sound('sent')

    def pick_file(self):
        if platform == 'android':
            try:
                from android import activity
                from jnius import autoclass, cast
                Intent = autoclass('android.content.Intent')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Intent.ACTION_GET_CONTENT)
                intent.setType('*/*')
                currentActivity = cast('android.app.Activity',
                                        PythonActivity.mActivity)
                currentActivity.startActivityForResult(intent, 0x1234)
                activity.bind(on_activity_result=self._on_file_picked)
            except Exception as e:
                print(f'file pick error: {e}')
        else:
            try:
                from tkinter import filedialog, Tk
                root = Tk()
                root.withdraw()
                path = filedialog.askopenfilename()
                root.destroy()
                if path:
                    self._send_file_path(path)
            except Exception as e:
                print(f'file dialog error: {e}')

    def _on_file_picked(self, requestCode, resultCode, intent):
        try:
            from android import activity
            activity.unbind(on_activity_result=self._on_file_picked)
        except: pass
        if resultCode != -1:
            return
        try:
            path = self._uri_to_path(intent.getData())
            if path:
                self._send_file_path(path)
        except Exception as e:
            print(f'_on_file_picked error: {e}')

    def _uri_to_path(self, uri):
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            context = PythonActivity.mActivity
            resolver = context.getContentResolver()
            cursor = resolver.query(uri, None, None, None, None)
            if cursor:
                idx = cursor.getColumnIndex('_display_name')
                cursor.moveToFirst()
                name = cursor.getString(idx)
                cursor.close()
                import tempfile
                tmp = os.path.join(tempfile.gettempdir(), name)
                ins = resolver.openInputStream(uri)
                BufferedInputStream = autoclass('java.io.BufferedInputStream')
                bis = BufferedInputStream(ins)
                buf = bytearray(8192)
                with open(tmp, 'wb') as f:
                    while True:
                        n = bis.read(buf)
                        if n <= 0: break
                        f.write(bytes(buf[:n]))
                return tmp
        except Exception as e:
            print(f'_uri_to_path error: {e}')
        return None

    def _send_file_path(self, path):
        app = App.get_running_app()
        if self.chat_type == 'private' and self.chat_ip:
            app.network.send_file(self.chat_ip, path, self.chat_username)
            self._render_bubble(f'📎 ارسال: {os.path.basename(path)}',
                                is_sent=True,
                                time_str=datetime.now().strftime('%H:%M'))


# ==================== App ====================
class LANChatApp(App):
    username = StringProperty('')
    current_status = StringProperty('آنلاین')
    colors = COLORS

    def fa_text(self, text):
        """helper برای KV: تبدیل متن فارسی به RTL"""
        return fa(text)

    def build(self):
        self.title = 'LAN Chat'
        self.network = NetworkManager(self)

        sm = ScreenManager()
        sm.add_widget(LoginScreen(name='login'))
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(ChatScreen(name='chat'))

        cfg = load_config()
        if cfg.get('auto_login') and cfg.get('username'):
            self.username = cfg['username']
            self.current_status = cfg.get('status', 'آنلاین')
            Clock.schedule_once(lambda dt: self.go_main(), 0.5)

        return sm

    def hex_to_rgba(self, h):
        h = h.lstrip('#')
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return (r, g, b, 1)

    def go_main(self):
        self.network.username = self.username
        self.network.running = True
        for target in [self.network._discovery_listener,
                       self.network._message_listener,
                       self.network._file_listener,
                       self.network._group_listener,
                       self.network._broadcast_loop,
                       self.network._cleanup_loop]:
            threading.Thread(target=target, daemon=True).start()
        self.root.current = 'main'
        self.network.get_groups()
        Clock.schedule_once(
            lambda dt: self.root.get_screen('main').rebuild_list(), 0.8)

    def update_peer(self, ip, username, status, old):
        try:
            if self.root.current == 'main':
                self.root.get_screen('main').rebuild_list()
        except: pass

    def remove_peer(self, ip, username):
        try:
            if self.root.current == 'main':
                self.root.get_screen('main').rebuild_list()
        except: pass

    def mark_message_pending(self, ip, msg_id):
        pass

    def flush_pending(self, peer_ip, peer_username):
        pendings = load_pending(self.username, peer_username)
        if not pendings:
            return
        play_sound('pending')
        for entry in pendings:
            mid = entry.get('id', f'{time.time():.6f}')
            content = entry.get('content', '')
            self.network.send_message(peer_ip, 'MSG', content,
                                      peer_username=peer_username,
                                      save_to_history=False, msg_id=mid)
            msgs = load_history(self.username, peer_username)
            for m in msgs:
                if m.get('id') == mid:
                    m['pending'] = False
                    break
            save_history(self.username, peer_username, msgs)
        clear_pending(self.username, peer_username)

    def receive_message(self, ip, msg):
        peer = self.network.peers.get(ip)
        uname = peer['username'] if peer else msg.get('username', ip)

        if msg.get('type') == 'MSG':
            entry = {
                'id': msg.get('msg_id', ''),
                'direction': 'received',
                'content': msg.get('content', ''),
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'deleted': False,
            }
            append_history(self.username, uname, entry)

        try:
            cs = self.root.get_screen('chat')
            if (self.root.current == 'chat' and
                cs.chat_username == uname and
                cs.chat_type == 'private'):
                if msg.get('type') == 'MSG':
                    t = datetime.now().strftime('%H:%M')
                    cs._render_bubble(msg.get('content', ''),
                                      is_sent=False, time_str=t)
                elif msg.get('type') == 'BUZZ':
                    cs._render_bubble('🔔 زنگ دریافت شد!',
                                      is_sent=False, time_str='')
        except: pass

        play_sound('msg')
        if self.root.current != 'chat':
            send_notification(fa(f'پیام از {uname}'),
                              fa(msg.get('content', '')[:100]))

        try:
            self.root.get_screen('main').rebuild_list()
        except: pass

    def receive_file_notification(self, ip, filename, save_path):
        peer = self.network.peers.get(ip)
        uname = peer['username'] if peer else ip
        send_notification(fa(f'فایل از {uname}'),
                          fa(f'دریافت شد: {filename}'))
        play_sound('file')

    def file_sent_notification(self, ip, filename):
        pass

    def receive_group_message(self, ip, msg):
        group_name = msg.get('group_name', '')
        if not group_name:
            return
        entry = {
            'id': msg.get('msg_id', f'{time.time():.6f}'),
            'username': msg.get('username', ''),
            'content': msg.get('content', ''),
            'time': msg.get('timestamp',
                            datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'deleted': False
        }
        append_group_history(group_name, entry)

        try:
            cs = self.root.get_screen('chat')
            if (self.root.current == 'chat' and
                cs.chat_type == 'group' and
                cs.chat_username == group_name):
                cs._render_history_group(entry)
        except: pass

        play_sound('group')
        if self.root.current != 'chat':
            send_notification(
                fa(f'گروه {group_name}'),
                fa(f'{entry["username"]}: {entry["content"][:80]}'))

    def add_group_message(self, group_name, entry):
        try:
            cs = self.root.get_screen('chat')
            if (self.root.current == 'chat' and
                cs.chat_type == 'group' and
                cs.chat_username == group_name):
                cs._render_history_group(entry)
        except: pass

    def on_pause(self):
        return True

    def on_resume(self):
        pass

    def on_stop(self):
        try:
            self.network.stop()
        except: pass


if __name__ == '__main__':
    LANChatApp().run()