from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

from hubModels.models import HubUser


class CookieAuthenticationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = HubUser.objects.create_user(
            first_name='Cookie', last_name='Test', email='cookie@example.com', password='TestPassword123!',
        )

    def login(self):
        response = self.client.post('/api/token/', {
            'email': self.user.email, 'password': 'TestPassword123!',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        return response

    def test_refresh_rotates_blacklists_and_never_returns_refresh_in_body(self):
        login = self.login()
        old = login.cookies['refresh_token'].value
        old_jti = RefreshToken(old)['jti']
        response = self.client.post('/api/token/refresh/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {'access_token'})
        self.assertIn('refresh_token', response.cookies)
        new = response.cookies['refresh_token']
        new_value = new.value
        self.assertNotEqual(new.value, old)
        self.assertTrue(new['httponly'])
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=old_jti).exists())
        self.client.cookies['refresh_token'] = old
        self.assertIn(self.client.post('/api/token/refresh/').status_code, (401, 403))
        self.client.cookies['refresh_token'] = new_value
        self.assertEqual(self.client.post('/api/token/refresh/').status_code, 200)

    def test_logout_deletes_cookie_and_revokes_token(self):
        old = self.login().cookies['refresh_token'].value
        old_jti = RefreshToken(old)['jti']
        response = self.client.post('/api/logout/')
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        self.assertEqual(response.cookies['refresh_token'].value, '')
        self.assertEqual(response.cookies['refresh_token']['max-age'], 0)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=old_jti).exists())
        self.client.cookies['refresh_token'] = old
        self.assertIn(self.client.post('/api/token/refresh/').status_code, (401, 403))
        self.assertEqual(self.client.post('/api/logout/').status_code, 204)

    def test_logout_is_idempotent_without_cookie_with_invalid_or_expired_token(self):
        expired = RefreshToken.for_user(self.user)
        expired['exp'] = 0
        for cookie in (None, 'not-a-token', str(expired)):
            with self.subTest(cookie=cookie):
                self.client.cookies.clear()
                if cookie:
                    self.client.cookies['refresh_token'] = cookie
                self.client.credentials(HTTP_AUTHORIZATION='Bearer expired-or-invalid')
                for _ in range(2):
                    response = self.client.post('/api/logout/')
                    self.assertEqual(response.status_code, 204)
                    self.assertEqual(response.cookies['refresh_token']['max-age'], 0)

    def test_inactive_user_cannot_refresh(self):
        self.login()
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertIn(self.client.post('/api/token/refresh/').status_code, (401, 403))

    def test_cookie_configuration_matches_on_login_refresh_and_logout(self):
        jwt_settings = dict(settings.SIMPLE_JWT, AUTH_COOKIE='custom_refresh',
                            AUTH_COOKIE_PATH='/api/', AUTH_COOKIE_DOMAIN='example.test',
                            AUTH_COOKIE_SAMESITE='Strict', AUTH_COOKIE_SECURE=True)
        with override_settings(SIMPLE_JWT=jwt_settings):
            login = self.login()
            self.assertIn('custom_refresh', login.cookies)
            refreshed = self.client.post('/api/token/refresh/')
            self.assertEqual(refreshed.status_code, 200)
            logout = self.client.post('/api/logout/')
            self.assertEqual(logout.status_code, 204)
            for response in (login, refreshed, logout):
                cookie = response.cookies['custom_refresh']
                self.assertEqual(cookie['path'], '/api/')
                self.assertEqual(cookie['domain'], 'example.test')
                self.assertEqual(cookie['samesite'], 'Strict')
            for response in (login, refreshed):
                self.assertTrue(response.cookies['custom_refresh']['httponly'])
                self.assertTrue(response.cookies['custom_refresh']['secure'])

    def test_refresh_accepts_only_cookie_not_body(self):
        token = self.login().cookies['refresh_token'].value
        self.client.cookies.clear()
        response = self.client.post('/api/token/refresh/', {'refresh': token}, format='json')
        self.assertIn(response.status_code, (401, 403))
