from sentry_sdk import capture_exception


def uncaught(error):
    capture_exception(error)
    return "Something unexpected happened.\nThe devs were notified of this incident."
