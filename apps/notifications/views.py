from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import NotificationLog
from .serializers import NotificationLogSerializer


class MyNotificationsView(generics.ListAPIView):
    """In-app notification inbox, backed by the same log used for push."""
    serializer_class = NotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return NotificationLog.objects.filter(user=self.request.user)


class MarkNotificationReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        NotificationLog.objects.filter(pk=pk, user=request.user).update(is_read=True)
        return Response({'detail': 'Marked as read.'})
