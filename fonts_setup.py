# fonts_setup.py
import os
from kivy.core.text import LabelBase

FONT_DIR = os.path.dirname(os.path.abspath(__file__))

def register_fonts():
    """ثبت فونت فارسی در Kivy"""
    # نام‌های مختلفی که ممکن است فایل فونت داشته باشد
    candidates_regular = [
        'Vazirmatn-Regular.ttf',
        'Vazir.ttf',
        'Sahel.ttf',
        'IRANSans.ttf',
        'BNAZANIN.TTF',
    ]
    candidates_bold = [
        'Vazirmatn-Bold.ttf',
        'Vazir-Bold.ttf',
        'Sahel-Bold.ttf',
        'IRANSans-Bold.ttf',
        'BNAZANB.TTF',
    ]

    regular = None
    for name in candidates_regular:
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            regular = p
            break

    bold = None
    for name in candidates_bold:
        p = os.path.join(FONT_DIR, name)
        if os.path.exists(p):
            bold = p
            break

    if regular:
        LabelBase.register(
            name='Vazir',
            fn_regular=regular,
            fn_bold=bold if bold else regular,
        )
        print(f'[FONT] Registered: {regular}')
        return 'Vazir'

    print(f'[FONT] WARNING: no Persian font found in {FONT_DIR}')
    print('[FONT] Using Roboto (Persian will show as boxes)')
    return 'Roboto'


# ==================== RTL Helper ====================
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    _RTL_AVAILABLE = True
    print('[RTL] arabic-reshaper + python-bidi loaded')
except ImportError:
    _RTL_AVAILABLE = False
    print('[RTL] WARNING: pip install arabic-reshaper python-bidi')


def fa(text):
    """آماده‌سازی متن فارسی برای نمایش در Kivy (RTL)"""
    if text is None:
        return ''
    text = str(text)
    if not text:
        return text
    # اگر متن فارسی/عربی ندارد، دست نزن
    if not any('\u0600' <= c <= '\u06FF' for c in text):
        return text
    if not _RTL_AVAILABLE:
        return text
    try:
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)
    except Exception as e:
        print(f'[RTL] error: {e}')
        return text