class Protocol:
    SEP = "\x01"

    # Game -> Server
    USER_TRANSCRIPT = "\x02"
    EVENT_TRIGGERED = "\x03"

    # Server -> Game
    AUDIO_MP3 = "\x11"
    SUBTITLE = "\x12"
    STATE_UPDATE = "\x13"
    EVENT_TRIGGER = "\x14"
