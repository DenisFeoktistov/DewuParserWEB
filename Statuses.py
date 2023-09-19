class BrowserStatuses:
    FREE = "free"
    PASSIVE_IN_WORK = "passive in work"
    AGGRESSIVE_RESERVED = "aggressive free"
    AGGRESSIVE_IN_WORK = "aggressive in work"
    MAIN_IN_WORK = "main in work"

    ALL = (FREE, PASSIVE_IN_WORK, AGGRESSIVE_RESERVED, AGGRESSIVE_IN_WORK, MAIN_IN_WORK)


class ErrorMessages:
    ALL_BROWSERS_ARE_BUSY = "All browsers are busy"
    ERROR = "Error"
    INTERRUPTED = "Interrapted"

    ALL = (ALL_BROWSERS_ARE_BUSY, ERROR, INTERRUPTED)
