from api.application import create_app as create_app_base
from mongoengine.connection import _get_db
import unittest
import json
from datetime import datetime, timedelta

from api.app.models import App, Access
from api.settings import MONGODB_HOST


class AppTest(unittest.TestCase):
    def create_app(self):
        self.db_name = 'bucketlist-api-test'
        return create_app_base(
            MONGODB_SETTINGS={'DB': self.db_name,
                              'HOST': MONGODB_HOST},
            TESTING=True,
            WTF_CSRF_ENABLED=False,
            SECRET_KEY='mySecret!',
        )

    def setUp(self):
        self.app_factory = self.create_app()
        self.app = self.app_factory.test_client()

    def tearDown(self):
        db = _get_db()
        db.client.drop_database(db)

    def app_dict(self):
        return json.dumps(dict(
            app_id="bucketlist_client",
            app_secret="bucketlist_secret"
        ))

    def test_create_app(self):
        # basic registration
        rv = self.app.post
        assert rv.status_code == 200

        # missing app_secret
        missing_app_dict = json.dumps(dict(
            app_id="bucketlist_client"
        ))
        rv = self.app.post
        assert "MISSING_APP_ID_OR_APP_SECRET" in str(rv.data)

        # repeat registration
        rv = self.app.post
        assert "APP_ID_ALREADY_EXISTS" in str(rv.data)

    def test_token_generation(self):
        rv = self.app.post
        assert rv.status_code == 200

        # generate access token
        rv = self.app.post
        token = json.loads(rv.data.decode('utf-8')).get('token')
        assert token is not None

        # missing app_secret
        missing_app_dict = json.dumps(dict(
            app_id="bucketlist_client"
        ))
        rv = self.app.post
        assert "MISSING_APP_ID_OR_APP_SECRET" in str(rv.data)

        # incorrect app_secret
        missing_app_dict = json.dumps(dict(
            app_id="bucketlist_client",
            app_secret="bad_bucketlist_secret"
        ))
        rv = self.app.post
        assert "INCORRECT_CREDENTIALS" in str(rv.data)

        # test that token works
        rv = self.app.get('/items/',
                          headers={
                              'X-APP-ID': 'bucketlist_client',
                              'X-APP-TOKEN': token},
                          content_type='application/json')
        assert rv.status_code == 200

        # test bad token
        rv = self.app.get('/items/',
                          headers={
                              'X-APP-ID': 'bucketlist_client',
                              'X-APP-TOKEN': 'bad-token'},
                          content_type='application/json')
        assert rv.status_code == 403

        # test expired token
        now = datetime.utcnow().replace(second=0, microsecond=0)
        expires = now + timedelta(days=-31)
        access = Access.objects.first()
        access.expires = expires
        access.save()
        rv = self.app.get('/items/',
                          headers={
                              'X-APP-ID': 'bucketlist_client',
                              'X-APP-TOKEN': token},
                          content_type='application/json')
        assert "TOKEN_EXPIRED" in str(rv.data)
