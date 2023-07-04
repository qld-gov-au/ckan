# encoding: utf-8

import logging
import ckan.lib.captcha as captcha
import ckan.lib.helpers as h

from zope.interface import implementer
from repoze.who.interfaces import IAuthenticator

from ckan.model import User

log = logging.getLogger(__name__)


@implementer(IAuthenticator)
class UsernamePasswordAuthenticator(object):

    def authenticate(self, environ, identity):
        if not ('login' in identity and 'password' in identity):
            return None

        if environ.get('__RECAPTCHA_DONE'):
            try:
                captcha.check_recaptcha(request)
                environ['__RECAPTCHA_DONE'] = True
            except captcha.CaptchaError:
                error_msg = _(u'Bad Captcha. Please try again.')
                h.flash_error(error_msg)
                return None


        login = identity['login']
        user = User.by_name(login)

        if user is None:
            log.debug('Login failed - username %r not found', login)
        elif not user.is_active():
            log.debug('Login as %r failed - user isn\'t active', login)
        elif not user.validate_password(identity['password']):
            log.debug('Login as %r failed - password not valid', login)
        else:
            return '{},{}'.format(
                user.id,
                1
            )

        return None
