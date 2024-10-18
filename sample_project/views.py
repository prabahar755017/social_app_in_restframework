from rest_framework.decorators import api_view,permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from .models import *
from rest_framework.permissions import IsAuthenticated,AllowAny
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q



User = get_user_model()

# Token generation function
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

# Signup view
@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    email = request.data.get('email')
    password = request.data.get('password')
    first_name = request.data.get('first_name')
    last_name = request.data.get('last_name')

    if not email or not password:
        return Response({"error": "Email and password are required"}, status=400)

    try:
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        return Response({"message": "User created successfully"}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)


# Login view
@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    email = request.data.get('email')
    password = request.data.get('password')
    
    user = authenticate(request, email=email, password=password)
    
    if user is not None:
        tokens = get_tokens_for_user(user)
        return Response(tokens, status=status.HTTP_200_OK)
    else:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
@permission_classes([AllowAny])
def search_users(request):
    keyword = request.GET.get('keyword', '')
    users = CustomUser.objects.filter(
        Q(email__iexact=keyword) | Q(first_name__icontains=keyword) | Q(last_name__icontains=keyword)
    )   
    
    paginator = Paginator(users, 10)  # Show 10 users per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    user_list = [{"email": user.email, "first_name": user.first_name, "last_name": user.last_name} for user in page_obj]
    return Response(user_list, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_friend_request(request):
    to_user_id = request.data.get('to_user_id')
    from_user = request.user

    # Check if user is sending more than 3 requests in a minute
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    sent_requests_count = FriendRequest.objects.filter(from_user=from_user, created_at__gte=one_minute_ago).count()

    if sent_requests_count >= 3:
        return Response({"error": "You cannot send more than 3 friend requests within a minute."}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    try:
        to_user = CustomUser.objects.get(id=to_user_id)
    except CustomUser.DoesNotExist:
        return Response({"error": "User does not exist."}, status=status.HTTP_404_NOT_FOUND)

    FriendRequest.objects.get_or_create(from_user=from_user, to_user=to_user)
    return Response({"success": "Friend request sent."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def accept_friend_request(request):
    request_id = request.data.get('request_id')
    friend_request = FriendRequest.objects.filter(id=request_id, to_user=request.user).first()

    if not friend_request:
        return Response({"error": "Friend request does not exist."}, status=status.HTTP_404_NOT_FOUND)

    friend_request.delete()  # Remove the request
    return Response({"success": "Friend request accepted."}, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_friend_request(request):
    request_id = request.data.get('request_id')
    friend_request = FriendRequest.objects.filter(id=request_id, to_user=request.user).first()

    if not friend_request:
        return Response({"error": "Friend request does not exist."}, status=status.HTTP_404_NOT_FOUND)

    friend_request.delete()  # Remove the request
    return Response({"success": "Friend request rejected."}, status=status.HTTP_200_OK)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_friends(request):
    friends = FriendRequest.objects.filter(to_user=request.user).values_list('from_user__email', flat=True)
    return Response(list(friends))

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_pending_requests(request):
    pending_requests = FriendRequest.objects.filter(to_user=request.user).values_list('from_user__email', flat=True)
    return Response(list(pending_requests))