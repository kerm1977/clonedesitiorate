from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
db=SQLAlchemy()
class User(UserMixin,db.Model):
    id=db.Column(db.Integer,primary_key=True)
    email=db.Column(db.String(120),unique=True,nullable=False)
    username=db.Column(db.String(80),unique=True,nullable=True)
    password_hash=db.Column(db.String(200),nullable=False)
    is_superuser=db.Column(db.Boolean,default=False)
    chat_alias=db.Column(db.String(100),nullable=True)  # Alias para mostrar en el chat
class Image(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    filename=db.Column(db.String(255),nullable=False)
    filepath=db.Column(db.String(500),unique=True,nullable=False)
    folder=db.Column(db.String(500))
    active=db.Column(db.Boolean,default=True)
    has_confetti=db.Column(db.Boolean,default=False)
    story=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    votes=db.relationship('ImageVote',backref='image',lazy=True,cascade='all, delete-orphan')

    @property
    def is_video(self):
        video_extensions = ('.mp4', '.webm', '.mov', '.avi', '.mkv', '.wmv', '.m4v', '.h264', '.264', '.mpeg', '.mpg', '.3gp', '.ts')
        return self.filename.lower().endswith(video_extensions)
class Message(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    text=db.Column(db.Text,nullable=False)
    label=db.Column(db.String(100))
    trigger_image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class AboutContent(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    content=db.Column(db.Text,default='')
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class AppConfig(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    key=db.Column(db.String(100),unique=True,nullable=False)
    value=db.Column(db.Text)
class FinalFeedback(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_session=db.Column(db.String(100),nullable=False)
    comment=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class ImageSource(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(100),nullable=False)
    source_type=db.Column(db.String(20),default='folder')
    path=db.Column(db.String(500))
    active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class SurveyQuestion(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    text=db.Column(db.String(500),nullable=False)
    order=db.Column(db.Integer,default=0)
    active=db.Column(db.Boolean,default=True)
    question_type=db.Column(db.String(20),default='text')
    options=db.Column(db.Text)
class SurveyResponse(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    question_id=db.Column(db.Integer,db.ForeignKey('survey_question.id'),nullable=False)
    answer=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('user_session','question_id'),)
class Favorite(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('user_session','image_id'),)
class Notification(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    message=db.Column(db.String(255),nullable=False)
    notification_type=db.Column(db.String(50),default='info')
    read=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class CollectionOpinion(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    filename=db.Column(db.String(255),nullable=False,index=True)
    username=db.Column(db.String(80),nullable=False)
    opinion=db.Column(db.Text,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

class ImageQuestion(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False)
    question=db.Column(db.String(500),nullable=False)
    trigger_rating=db.Column(db.Integer,default=200)
    active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class ImageQuestionResponse(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    question_id=db.Column(db.Integer,db.ForeignKey('image_question.id'),nullable=False)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    answer=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('question_id','user_session'),)
class RatingFiveFeedback(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    what_you_think=db.Column(db.Text)
    what_you_like=db.Column(db.Text)
    what_you_would_do=db.Column(db.Text)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('image_id','user_session'),)
class ScheduledUserMessage(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    message=db.Column(db.Text,nullable=False)
    scheduled_at=db.Column(db.DateTime,nullable=True)  # Null para mensajes inmediatos
    shown=db.Column(db.Boolean,default=False)
    response=db.Column(db.Text,nullable=True)  # Respuesta del usuario
    responded_at=db.Column(db.DateTime,nullable=True)  # Cuándo respondió
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='scheduled_messages')
class PushSubscription(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    username=db.Column(db.String(100),nullable=True,index=True)
    endpoint=db.Column(db.Text,nullable=False)
    p256dh=db.Column(db.String(255),nullable=False)
    auth=db.Column(db.String(255),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
class Story(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_session=db.Column(db.String(100),nullable=False,index=True)
    title=db.Column(db.String(200),nullable=False)
    content=db.Column(db.Text,nullable=False)
    admin_comments=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
    comments=db.relationship('StoryComment',backref='story',lazy=True)
class WeeklyStory(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(200),nullable=False)
    content=db.Column(db.Text,nullable=False)
    author=db.Column(db.String(200),nullable=False)
    week_start=db.Column(db.DateTime,nullable=False)
    active=db.Column(db.Boolean,default=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    updated_at=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class WeeklyStoryComment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    weekly_story_id=db.Column(db.Integer,db.ForeignKey('weekly_story.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    user_session=db.Column(db.String(100),nullable=True)
    username=db.Column(db.String(100),nullable=False)
    content=db.Column(db.Text,nullable=False)
    likes_count=db.Column(db.Integer,default=0)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    weekly_story=db.relationship('WeeklyStory',backref='comments')
    user=db.relationship('User',backref='weekly_comments')
class StoryComment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    story_id=db.Column(db.Integer,db.ForeignKey('story.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    user_session=db.Column(db.String(100),nullable=True)
    username=db.Column(db.String(100),nullable=False)
    content=db.Column(db.Text,nullable=False)
    likes_count=db.Column(db.Integer,default=0)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='story_comments')
class LoginAttempt(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    ip_address=db.Column(db.String(100),nullable=False,index=True)
    failed_count=db.Column(db.Integer,default=0)
    blocked=db.Column(db.Boolean,default=False)
    last_attempt=db.Column(db.DateTime,default=datetime.utcnow,onupdate=datetime.utcnow)
class RateLimit(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    ip_address=db.Column(db.String(100),nullable=False,index=True,unique=True)
    request_count=db.Column(db.Integer,default=0)
    window_start=db.Column(db.DateTime,default=datetime.utcnow)
class ImageComment(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    user_session=db.Column(db.String(100),nullable=True)
    username=db.Column(db.String(100),nullable=False)
    content=db.Column(db.Text,nullable=False)
    likes_count=db.Column(db.Integer,default=0)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    image=db.relationship('Image',backref='comments')
    user=db.relationship('User',backref='image_comments')
class CommentRead(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    user_session=db.Column(db.String(100),nullable=True)
    comment_type=db.Column(db.String(50),nullable=False)  # 'weekly' o 'story'
    comment_id=db.Column(db.Integer,nullable=False)
    read_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('user_id','user_session','comment_type','comment_id'),)

class CommentLike(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    user_session=db.Column(db.String(100),nullable=True)
    comment_type=db.Column(db.String(50),nullable=False)  # 'weekly' o 'story'
    comment_id=db.Column(db.Integer,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('user_id','user_session','comment_type','comment_id'),)
class ChatMessage(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    sender_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    sender_session=db.Column(db.String(100),nullable=True)
    sender_name=db.Column(db.String(100),nullable=False)
    receiver_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    receiver_session=db.Column(db.String(100),nullable=True)
    receiver_name=db.Column(db.String(100),nullable=False)
    chat_display_name=db.Column(db.String(100),nullable=True)  # Nombre personalizado del chat por superusuario
    chat_type=db.Column(db.String(20),default='private')  # 'private' o 'moderator'
    content=db.Column(db.Text,nullable=True)  # Puede ser null si es imagen
    image_path=db.Column(db.String(255),nullable=True)  # Ruta de la imagen
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    is_read=db.Column(db.Boolean,default=False)
    edited=db.Column(db.Boolean,default=False)  # Indica si el mensaje fue editado
    edited_at=db.Column(db.DateTime,nullable=True)  # Timestamp de edición
    sender=db.relationship('User',foreign_keys=[sender_id],backref='sent_messages')
    receiver=db.relationship('User',foreign_keys=[receiver_id],backref='received_messages')
class DeletedImage(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    filename=db.Column(db.String(255),nullable=False)
    deleted_by_user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    deleted_at=db.Column(db.DateTime,default=datetime.utcnow)
    deleted_by=db.relationship('User',backref='deleted_images')

class ImageVote(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False,index=True)
    vote_type=db.Column(db.String(10),nullable=False)  # 'like' o 'dislike'
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    __table_args__=(db.UniqueConstraint('image_id','user_id'),)
    user=db.relationship('User',backref='image_votes')

class FakeUserCategory(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(200),nullable=False)
    order=db.Column(db.Integer,default=0)
    users=db.relationship('FakeUser',backref='category',lazy=True,cascade='all, delete-orphan',order_by='FakeUser.order')

class FakeUser(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    category_id=db.Column(db.Integer,db.ForeignKey('fake_user_category.id'),nullable=False)
    name=db.Column(db.String(100),nullable=False)
    order=db.Column(db.Integer,default=0)

class ActivityLog(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    username=db.Column(db.String(80),nullable=False,index=True)
    action=db.Column(db.String(50),nullable=False)  # download, view, comment, like
    object_type=db.Column(db.String(50),nullable=False)  # image, collection_file, weekly_comment, image_comment, story_comment
    object_id=db.Column(db.String(100),nullable=True)
    object_name=db.Column(db.String(255),nullable=False)
    object_url=db.Column(db.String(500),nullable=True)
    extra=db.Column(db.Text,nullable=True)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)

class ImageDownload(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    image_id=db.Column(db.Integer,db.ForeignKey('image.id'),nullable=False,index=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True,index=True)
    user_session=db.Column(db.String(100),nullable=True)
    username=db.Column(db.String(100),nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    image=db.relationship('Image',backref='downloads')

class Topic(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    title=db.Column(db.String(200),nullable=False)
    description=db.Column(db.Text,nullable=True)
    link=db.Column(db.String(500),nullable=True)
    image_path=db.Column(db.String(500),nullable=True)
    published_at=db.Column(db.DateTime,default=datetime.utcnow)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='topics')
    replies=db.relationship('TopicReply',backref='topic',lazy=True,cascade='all, delete-orphan',order_by='TopicReply.created_at')

class TopicReply(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    topic_id=db.Column(db.Integer,db.ForeignKey('topic.id'),nullable=False)
    user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    display_name=db.Column(db.String(100),nullable=True)
    content=db.Column(db.Text,nullable=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    user=db.relationship('User',backref='topic_replies')

class AdminNotification(db.Model):
    __tablename__='admin_notification'
    id=db.Column(db.Integer,primary_key=True)
    recipient_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False)
    actor_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=True)
    type=db.Column(db.String(50),nullable=False,default='nita_topic_reply')
    topic_id=db.Column(db.Integer,db.ForeignKey('topic.id'),nullable=True)
    reply_id=db.Column(db.Integer,db.ForeignKey('topic_reply.id'),nullable=True)
    message=db.Column(db.Text,nullable=False)
    is_read=db.Column(db.Boolean,default=False)
    created_at=db.Column(db.DateTime,default=datetime.utcnow)
    recipient=db.relationship('User',foreign_keys=[recipient_id],backref='admin_notifications',lazy=True)
    actor=db.relationship('User',foreign_keys=[actor_id],backref='admin_notifications_sent',lazy=True)
    topic=db.relationship('Topic',backref='admin_notifications')
    reply=db.relationship('TopicReply',backref='admin_notifications')
