
def is_fastapi_present():
    # noinspection PyPep8,PyBroadException
    try:
        import fastapi
        import starlette
        return True
    except:
        return False


if is_fastapi_present():
    from .implementation import FastAPIAppRequestInstrumentationConfigurator, FastAPIRequestInfoExtractor, \
        FastAPIResponseInfoExtractor
