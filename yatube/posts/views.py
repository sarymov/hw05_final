from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PostForm, CommentForm
from .models import Group, Post, User, Comment, Follow

PAGINATOR_VALUE = 10


def paginate_func(request, posts):
    paginator = Paginator(posts, PAGINATOR_VALUE)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)


def index(request):

    post_list = Post.objects.select_related("group", "author")
    page_obj = paginate_func(request, post_list)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.select_related('author')
    page_obj = paginate_func(request, posts)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    posts = author.posts.select_related('author', 'group')
    page_obj = paginate_func(request, posts)

    context = {
        'author': author,
        'page_obj': page_obj,
        'postscount': posts.count(),
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post=post)

    context = {
        'post': post,
        'form': form,
        'comments': comments,

    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None,)
    if not form.is_valid() or not request.method == "POST":
        return render(request, 'posts/create_post.html', {'form': form})

    post = form.save(commit=False)
    post.author = request.user
    post.save()
    return redirect('posts:profile', request.user)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if post.author != request.user:
        return redirect('posts:post_detail', post.pk)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=post)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post.pk)

    return render(request, 'posts/create_post.html',
                  {'form': form, 'is_edit': True, 'post': post})


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, PAGINATOR_VALUE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    if request.user.username != username:
        author = get_object_or_404(User, username=username)
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    if request.user.username != username:
        author = get_object_or_404(User, username=username)
        Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:follow_index')
