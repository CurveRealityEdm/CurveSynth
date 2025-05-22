import numpy as np
import sounddevice as sd
import os

fs = 44100  # частота дискретизации

# параметры ADSR (в секундах)
attack, decay, sustain, release = 0.01, 0.1, 0.7, 0.2

# параметры стерео и микширования
detune = 0.0    # детюн в центах
volume = 0.8    # громкость 0.0–1.0
pan = 0.0       # панорама -1 (лево) – +1 (право)

# внутреннее состояние осцилляторов
_freq = 440.0
_tbl_phase1 = _tbl_phase2 = 0.0
_tbl_inc1 = _tbl_inc2 = 0.0

_state = 'idle'   # текущее состояние огибающей: 'idle', 'on', 'off'
_env_level = 0.0  # текущий уровень огибающей
_env_stage = 0    # стадия огибающей: 0=Attack,1=Decay,2=Sustain,3=Release

# хранилище волновых таблиц
TABLE_SIZE = 2048
_wavetables = {}
_current_table = None

# кольцевой буфер для визуализации звука
BUFFER_SIZE = 1024
_last_buffer = np.zeros((BUFFER_SIZE, 2), dtype=float)

def _generate_wavetables():
    """Генерация базовых волновых таблиц и загрузка дополнительных из папки."""
    t = np.linspace(0, 1, TABLE_SIZE, endpoint=False)
    _wavetables['Sine']     = np.sin(2 * np.pi * t)
    _wavetables['Square']   = np.sign(np.sin(2 * np.pi * t))
    _wavetables['Saw']      = 2 * (t - np.floor(t + 0.5))
    _wavetables['Triangle'] = 2 * np.abs(2 * (t - np.floor(t + 0.5))) - 1
    _wavetables['Noise']    = np.random.uniform(-1.0, 1.0, TABLE_SIZE)

    # загрузка любых .npy-файлов из ./wavetables
    wt_dir = os.path.join(os.path.dirname(__file__), 'wavetables')
    if os.path.isdir(wt_dir):
        for fn in os.listdir(wt_dir):
            if fn.lower().endswith('.npy'):
                name = os.path.splitext(fn)[0]
                arr = np.load(os.path.join(wt_dir, fn))
                if arr.shape[0] != TABLE_SIZE:
                    # приведение длины к TABLE_SIZE
                    arr = np.interp(
                        np.linspace(0, 1, TABLE_SIZE, endpoint=False),
                        np.linspace(0, 1, arr.shape[0], endpoint=False),
                        arr
                    )
                _wavetables[name] = arr

    set_wavetable('Sine')

def set_wavetable(name):
    """Выбор волновой таблицы по имени."""
    global _current_table
    if name in _wavetables:
        _current_table = _wavetables[name]
    else:
        raise ValueError(f"Волновая таблица '{name}' не найдена.")

def update_deltas():
    """Пересчет приращений фазы для двух голосов с учетом детюна."""
    global _tbl_inc1, _tbl_inc2
    f1 = _freq * (2 ** (detune / 1200.0))
    f2 = _freq * (2 ** (-detune / 1200.0))
    _tbl_inc1 = f1 * TABLE_SIZE / fs
    _tbl_inc2 = f2 * TABLE_SIZE / fs

def set_freq(f):
    """Установка частоты и сброс фаз."""
    global _freq, _tbl_phase1, _tbl_phase2
    _freq = f
    _tbl_phase1 = _tbl_phase2 = 0.0
    update_deltas()

def set_detune(cents):
    """Установка детюна и пересчет фаз."""
    global detune
    detune = cents
    update_deltas()

def set_volume(v):
    """Установка громкости."""
    global volume
    volume = v

def set_pan(p):
    """Установка панорамы."""
    global pan
    pan = p

def set_adsr(a, d, s, r):
    """Установка параметров ADSR."""
    global attack, decay, sustain, release
    attack, decay, sustain, release = a, d, s, r

def note_on():
    """Начало ноты (вход в стадию Attack)."""
    global _state, _env_stage
    _state = 'on'
    _env_stage = 0

def note_off():
    """Отпускание ноты (переход в стадию Release)."""
    global _state, _env_stage
    if _state != 'idle':
        _state = 'off'
        _env_stage = 3

def _adsr_step():
    """Шаг огибающей ADSR: вычисление нового уровня."""
    global _env_level, _env_stage, _state
    if _env_stage == 0:  # Attack
        _env_level += 1.0 / (attack * fs)
        if _env_level >= 1.0:
            _env_level, _env_stage = 1.0, 1
    elif _env_stage == 1:  # Decay
        _env_level -= (1.0 - sustain) / (decay * fs)
        if _env_level <= sustain:
            _env_level, _env_stage = sustain, 2
    elif _env_stage == 2:  # Sustain (держим уровень)
        pass
    elif _env_stage == 3:  # Release
        _env_level -= sustain / (release * fs)
        if _env_level <= 0.0:
            _env_level, _state = 0.0, 'idle'
    return _env_level

def get_buffer():
    """Возвращает копию последнего BUFFER_SIZE стерео-сэмплов для визуализации."""
    return _last_buffer.copy()

def callback(outdata, frames, time, status):
    """Аудио-колбэк: генерирует звук и заполняет ring-buffer."""
    global _tbl_phase1, _tbl_phase2, _last_buffer
    idx = np.arange(frames)
    ts1 = (_tbl_phase1 + idx * _tbl_inc1) % TABLE_SIZE
    ts2 = (_tbl_phase2 + idx * _tbl_inc2) % TABLE_SIZE
    wave1 = _current_table[ts1.astype(int)]
    wave2 = _current_table[ts2.astype(int)]
    env   = np.array([_adsr_step() for _ in range(frames)])
    left  = wave1 * env * volume * (1 - max(0, pan))
    right = wave2 * env * volume * (1 - max(0, -pan))

    # обновление фаз
    _tbl_phase1 = ts1[-1] + _tbl_inc1
    _tbl_phase2 = ts2[-1] + _tbl_inc2

    # вывод в буфер звука
    outdata[:, 0] = left
    outdata[:, 1] = right

    # обновление кольцевого буфера для визуализации
    buf = np.roll(_last_buffer, -frames, axis=0)
    buf[-frames:, 0] = left
    buf[-frames:, 1] = right
    _last_buffer[:] = buf

# инициализация волновых таблиц и запуск аудио-потока
_generate_wavetables()
_stream = sd.OutputStream(
    samplerate=fs, channels=2,
    callback=callback, blocksize=512
)
_stream.start()
