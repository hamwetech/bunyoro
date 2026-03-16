from django.conf import settings # import the settings file

def product_name(request):
    # return the value you want as a dictionnary. you may add multiple values in there.
    return {'product_name': settings.PRODUCT_NAME, 'product_abbreviation': settings.PRODUCT_ABBREVIATION}