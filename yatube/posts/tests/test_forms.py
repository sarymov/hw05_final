import tempfile
import shutil
from http import HTTPStatus
from posts.models import Group, Post, Comment
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile

from django.urls import reverse


User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateFormTests(TestCase):
    def setUp(self):
        self.not_authorized = Client()
        self.user = User.objects.create(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая группа',
            slug='slug',
            description='Тестовая группа'
        )
        self.post = Post.objects.create(
            text='Тестовый текст',
            group=self.group,
            author=self.user
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_post_create(self):
        posts_count = Post.objects.count()
        form_data = {
            'group': self.group.id,
            'text': 'Наш новый и уникальный Тестовый текст',
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user})
        )
        post = Post.objects.first()
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.author, self.user)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                group=form_data['group'],
            ).exists()
        )

    def test_post_edit(self):
        post = Post.objects.get(pk=self.post.id)
        self.new_group = Group.objects.create(
            title='Тестовая группа2',
            slug='test-slug',
            description='Тестовое описание',
        )
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Наш уникальный текст изменили, ау',
            'group': self.new_group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(Post.objects.filter(
            group=self.new_group.id,
            author=self.user,
            pub_date=self.post.pub_date
        ).exists()
        )
        post = Post.objects.get(pk=self.post.id)
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_authorized_comment(self):

        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый коммент',
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                post=self.post,
                text='Тестовый коммент',
                author=self.user,
            ).exists())

    def test_not_authorized_comment(self):

        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый коммент',
        }
        self.not_authorized.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertNotEqual(Comment.objects.count(), comments_count + 1)

    def test_create_group_post_form(self):
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded,
        }
        self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text='Тестовый текст',
                group=self.group.id,
                author=self.user,
                image='posts/small.gif'
            ).exists())

        post = Post.objects.get(pk=self.post.id)
        self.assertTrue(post.text, form_data['text'])
        self.assertTrue(post.group.id, form_data['group'])
        self.assertTrue(post.author, self.user)
        self.assertTrue(uploaded, form_data['image'])
