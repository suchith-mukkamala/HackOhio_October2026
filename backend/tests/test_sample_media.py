"""Sample-media replacements never modify real users or manually attached files."""
import unittest
import base64
import xml.etree.ElementTree as ET
import test_messaging
from app.models import User, Post
import seed_home


class SampleMediaTests(unittest.TestCase):
    setUp = test_messaging.MessagingTests.setUp
    tearDown = test_messaging.MessagingTests.tearDown

    def test_only_known_stock_media_on_exact_sample_posts_is_refreshed(self):
        sample = User(username='sample_aisha', name='Sample Aisha')
        self.session.add(sample); self.session.commit()
        photo = seed_home.POSTS[1]
        video = seed_home.POSTS[4]
        old_photo = Post(author_id=sample.id, body=photo[2], media_url='https://picsum.photos/seed/usability-test/1200/675', media_kind='image')
        old_video = Post(author_id=sample.id, body=video[2], media_url='https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4', media_kind='video')
        real = Post(author_id=self.actor.id, body=photo[2], media_url=old_photo.media_url, media_kind='image')
        custom = Post(author_id=sample.id, body=photo[2], media_url='https://example.com/real-upload.png', media_kind='image')
        self.session.add_all([old_photo, old_video, real, custom]); self.session.commit()
        result = seed_home.refresh_sample_media(self.session); self.session.commit()
        self.assertEqual(result['updated_sample_posts'], 2)
        self.assertTrue(old_photo.media_url.startswith('data:image/svg+xml;base64,'))
        self.assertIn('DELAYED', base64.b64decode(old_photo.media_url.split(',',1)[1]).decode())
        self.assertTrue(old_video.media_url.startswith('data:video/mp4;base64,'))
        self.assertIn(b'ftyp', base64.b64decode(old_video.media_url.split(',',1)[1])[:32])
        self.assertTrue(real.media_url.startswith('https://picsum.photos'))
        self.assertEqual(custom.media_url, 'https://example.com/real-upload.png')
        self.assertEqual(seed_home.refresh_sample_media(self.session)['updated_sample_posts'], 0)

    def test_assets_are_valid_and_related_to_posts(self):
        expected = {'rover-arm.svg':'rover arm', 'bus-arrivals.svg':'DELAYED', 'study-room.svg':'Thompson Library', 'data-project.svg':'Question'}
        for filename, topic in expected.items():
            svg=(seed_home.MEDIA_DIR/filename).read_text()
            ET.fromstring(svg)
            self.assertIn(topic, svg)
            self.assertIn('ILLUSTRATIVE SAMPLE', svg)
        self.assertLess((seed_home.MEDIA_DIR/'onboarding.mp4').stat().st_size, 3_000_000)
