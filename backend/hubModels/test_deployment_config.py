import importlib
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
from unittest import TestCase
from unittest.mock import patch

from decouple import Config
from django.core.exceptions import ImproperlyConfigured


class BooleanEnvironmentTestCase(TestCase):
    def test_supported_boolean_values(self):
        parse_bool = importlib.import_module('hubSettings.env').parse_bool
        for value in (True, 'true', 'TRUE', '  true ', '1', 1, 'yes', 'YeS'):
            with self.subTest(value=value):
                self.assertIs(parse_bool(value), True)
        for value in (False, 'false', 'FALSE', ' false ', '0', 0, 'no', 'NO'):
            with self.subTest(value=value):
                self.assertIs(parse_bool(value), False)

    def test_invalid_values_name_the_setting(self):
        parse_bool = importlib.import_module('hubSettings.env').parse_bool
        for value in ('release', '', '2', 'on', 'off', None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ImproperlyConfigured, 'DEBUG.*true/false/1/0/yes/no'):
                    parse_bool(value)
        with self.assertRaisesRegex(ImproperlyConfigured, 'AUTH_COOKIE_SECURE'):
            parse_bool('release', 'AUTH_COOKIE_SECURE')

    def load_settings(self, **environment):
        with patch('decouple.config', Config({})), patch.dict(
            os.environ, {'SECRET_KEY': 'isolated-settings-test-key', **environment}, clear=True,
        ):
            return runpy.run_path(str(Path(__file__).resolve().parents[1] / 'hubSettings' / 'settings.py'))

    def test_default_debug_is_false_and_cookie_is_secure(self):
        settings = self.load_settings()
        self.assertIs(settings['DEBUG'], False)
        self.assertIs(settings['SIMPLE_JWT']['AUTH_COOKIE_SECURE'], True)

    def test_debug_and_secure_cookie_can_be_set_explicitly(self):
        settings = self.load_settings(DEBUG='yes')
        self.assertIs(settings['DEBUG'], True)
        self.assertIs(settings['SIMPLE_JWT']['AUTH_COOKIE_SECURE'], False)
        settings = self.load_settings(DEBUG='false', AUTH_COOKIE_SECURE='0')
        self.assertIs(settings['DEBUG'], False)
        self.assertIs(settings['SIMPLE_JWT']['AUTH_COOKIE_SECURE'], False)
        settings = self.load_settings(DEBUG='true', AUTH_COOKIE_SECURE='yes')
        self.assertIs(settings['SIMPLE_JWT']['AUTH_COOKIE_SECURE'], True)
        with self.assertRaisesRegex(ImproperlyConfigured, 'DEBUG'):
            self.load_settings(DEBUG='release')
        with self.assertRaisesRegex(ImproperlyConfigured, 'AUTH_COOKIE_SECURE'):
            self.load_settings(AUTH_COOKIE_SECURE='release')

    def test_e2e_http_cookie_is_explicit_without_mutating_base_settings(self):
        base = importlib.import_module('hubSettings.settings')
        with patch.dict(base.SIMPLE_JWT, AUTH_COOKIE_SECURE=True):
            e2e = runpy.run_module('hubSettings.settings_e2e')
            self.assertIs(e2e['DEBUG'], True)
            self.assertIs(e2e['SIMPLE_JWT']['AUTH_COOKIE_SECURE'], False)
            self.assertIs(base.SIMPLE_JWT['AUTH_COOKIE_SECURE'], True)


class EntrypointSeedGateTestCase(TestCase):
    def run_entrypoint(self, **flags):
        entrypoint = Path(__file__).resolve().parents[1] / 'entrypoint.sh'
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            log = folder / 'calls.log'
            for command in ('python', 'gunicorn'):
                executable = folder / command
                executable.write_text(f'#!/bin/sh\nprintf "%s\\n" "{command} $*" >> "$CALL_LOG"\n')
                executable.chmod(0o755)
            environment = {key: value for key, value in os.environ.items()
                           if key not in ('SEED_DEMO', 'SEED_DEMO_FORCE')}
            environment.update(PATH=f"{folder}:{os.environ.get('PATH', '')}", CALL_LOG=str(log), **flags)
            subprocess.run(['/bin/sh', str(entrypoint)], env=environment, check=True,
                           capture_output=True, text=True)
            return log.read_text().splitlines()

    def test_default_false_and_force_alone_never_seed(self):
        for flags in ({}, {'SEED_DEMO': 'false'}, {'SEED_DEMO_FORCE': 'true'}, {'SEED_DEMO': 'yes'}):
            with self.subTest(flags=flags):
                commands = self.run_entrypoint(**flags)
                self.assertFalse(any('seed_demo' in command for command in commands))
                self.assertEqual(commands[0], 'python manage.py migrate --noinput')
                self.assertTrue(commands[-1].startswith('gunicorn '))

    def test_seed_without_force(self):
        commands = self.run_entrypoint(SEED_DEMO='true')
        self.assertEqual([command for command in commands if 'seed_demo' in command],
                         ['python manage.py seed_demo'])
        commands = self.run_entrypoint(SEED_DEMO='true', SEED_DEMO_FORCE='false')
        self.assertIn('python manage.py seed_demo', commands)

    def test_force_requires_both_flags(self):
        commands = self.run_entrypoint(SEED_DEMO='true', SEED_DEMO_FORCE='true')
        self.assertEqual([command for command in commands if 'seed_demo' in command],
                         ['python manage.py seed_demo --force'])


class RenderDeploymentPolicyTestCase(TestCase):
    def test_render_secret_is_generated_or_supplied_without_hardcoding(self):
        import re
        render = (Path(__file__).resolve().parents[2] / 'render.yaml').read_text()
        secret = render.split('- key: SECRET_KEY', 1)[1].split('- key:', 1)[0]
        self.assertTrue(re.search(r'generateValue:\s*true|sync:\s*false', secret),
                        'Render SECRET_KEY must use generateValue: true or sync: false.')
        self.assertNotIn('generateCryptoKey:', secret)
        self.assertNotRegex(secret, r'\bvalue:')


class ComposeReadinessTestCase(TestCase):
    def test_frontend_and_scheduler_wait_for_backend_readiness(self):
        import re
        compose = (Path(__file__).resolve().parents[2] / 'docker-compose.yml').read_text()
        sections = list(re.finditer(r'^  ([\w-]+):\s*$', compose, re.MULTILINE))
        blocks = {match.group(1): compose[match.end():sections[i + 1].start() if i + 1 < len(sections) else len(compose)]
                  for i, match in enumerate(sections)}
        self.assertIn('healthcheck:', blocks['backend'])
        self.assertIn('http://127.0.0.1:8008/api/', blocks['backend'])
        for service in ('recurring-scheduler', 'frontend'):
            with self.subTest(service=service):
                self.assertRegex(blocks[service], r'depends_on:\s*\n\s+backend:\s*\n\s+condition:\s+service_healthy')
