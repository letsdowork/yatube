from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow


def index(request):
    """Возвращает 10 записей на странице."""
    post_list = list(
        Post.objects.all().select_related(
            'author', 'group'
        ).prefetch_related('comments')
    )
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, 'index.html', {'page': page, 'paginator': paginator}
    )


def group_posts(request, slug):
    """Возвращает до 10 записей группы или ошибку, если группы нет."""
    group = get_object_or_404(Group, slug=slug)
    post_list = list(
        group.posts.all().select_related(
            'author').prefetch_related('comments')
    )
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request, 'group.html', {
        'page': page, 'paginator': paginator, 'group': group,
    })


@login_required()
def new_post(request):
    """Добавить новую запись, если пользователь известен."""
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')
    return render(request, 'new_post.html', {'form': form, 'upd': False})


def profile(request, username):
    """Профиль пользователя. Отображает записи и статистику по записям."""
    author = get_object_or_404(User, username=username)
    posts = list(
        author.posts.all().select_related(
            'group').prefetch_related('comments')
    )
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    post_count = paginator.count
    follower_count = author.following.count()
    follows_count = author.follower.count()
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=author
    ).exists()
    return render(request, 'profile.html', {
        'page': page, 'paginator': paginator, 'author': author,
        'posts': posts, 'post_count': post_count, 'following': following,
        'follower_count': follower_count, 'follows_count': follows_count,
    })


def post_view(request, username, post_id):
    """Отображает выбранную запись пользователя."""
    post = get_object_or_404(
        Post.objects.all().select_related(
            'group', 'author'
        ).prefetch_related('comments'), pk=post_id, author__username=username)
    author = post.author
    post_count = author.posts.count
    form = CommentForm()
    items = post.comments.all()
    follower_count = author.following.count()
    follows_count = author.follower.count()
    following = request.user.is_authenticated and Follow.objects.filter(
        user=request.user, author=author
    ).exists()
    return render(request, 'post.html', {
        'author': author, 'post': post, 'post_count': post_count,
        'form': form, 'items': items, 'follower_count': follower_count,
        'follows_count': follows_count, 'following': following,
    })


@login_required()
def post_edit(request, username, post_id):
    """Редактирование существующей записи."""
    post = get_object_or_404(
        Post.objects.all().select_related(
            'group', 'author'
        ), pk=post_id, author__username=username)
    if post.author != request.user:
        return redirect('post', username=username, post_id=post_id)
    form = PostForm(
        request.POST or None, files=request.FILES or None, instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('post', username=username, post_id=post_id)
    return render(request, 'new_post.html', {
        'form': form, 'upd': True, 'post': post
    })


def page_not_found(request, exception):
    return render(
        request,
        'misc/404.html',
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, 'misc/500.html', status=500)


@login_required()
def add_comment(request, username, post_id):
    post = get_object_or_404(Post, pk=post_id, author__username=username)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    """Лента постов по подпискам пользователя."""
    post_list = Post.objects.filter(
        author__following__user=request.user
    ).select_related('group', 'author').prefetch_related('comments')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request, "follow.html", {'page': page, 'paginator': paginator}
    )


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect('profile', username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    if request.user != author:
        Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('profile', username=username)
