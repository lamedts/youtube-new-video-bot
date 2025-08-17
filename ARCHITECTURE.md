# Clean Architecture Documentation

This document explains the refactored architecture of the YouTube Video Bot, following clean code principles and SOLID design patterns with **Firebase-only data persistence**.

## 🏗️ Architecture Overview

The refactored codebase follows a **layered architecture** with clear separation of concerns and **cloud-first data storage**:

```
src/
├── config/          # Configuration management
├── models/          # Data models and business entities
├── services/        # Business logic and external integrations
└── utils/           # Utility functions (if needed)
```

## ☁️ Firebase-Only Architecture

This version eliminates local file storage in favor of a pure cloud-based approach:

- **No local state files**: All data lives in Firebase Firestore
- **Real-time synchronization**: State is always current across restarts
- **Scalable design**: Ready for multi-instance deployments
- **Single source of truth**: Firebase is the authoritative data store

## 📋 SOLID Principles Applied

### Single Responsibility Principle (SRP)
- Each class has one reason to change
- `TelegramService` only handles Telegram operations
- `YouTubeService` only handles YouTube API operations
- `FirebaseService` only handles Firebase operations

### Open/Closed Principle (OCP)
- Services are open for extension, closed for modification
- `FirebaseRepository` protocol allows different Firebase implementations
- `NullFirebaseService` implements the same interface for graceful degradation

### Liskov Substitution Principle (LSP)
- `NullFirebaseService` can replace `FirebaseService` without breaking functionality
- Both implement the same `FirebaseRepository` protocol

### Interface Segregation Principle (ISP)
- `FirebaseRepository` protocol defines only necessary methods
- Services depend on abstractions, not concrete implementations

### Dependency Inversion Principle (DIP)
- High-level modules don't depend on low-level modules
- `YouTubeBotService` depends on service abstractions
- Dependencies are injected through constructors

## 📁 Module Breakdown

### `src/config/settings.py`
**Purpose**: Centralized configuration management

**Key Features**:
- Immutable `BotConfig` dataclass
- Environment variable validation
- Type-safe configuration access

```python
config = BotConfig.from_env()
config.validate()
```

### `src/models/`
**Purpose**: Business entities and data structures

**Key Components**:
- `Video`: Represents YouTube video data
- `Channel`: Represents YouTube channel subscription
- `UserChannelInfo`: Authenticated user's channel info

**Benefits**:
- Type safety with dataclasses
- Immutable where appropriate
- Conversion methods for different storage formats

### `src/services/firebase_service.py`
**Purpose**: Firebase/Firestore operations

**Key Features**:
- Protocol-based design for testability
- Graceful degradation with `NullFirebaseService`
- Proper error handling and logging

### `src/services/youtube_service.py`
**Purpose**: YouTube API and RSS operations

**Key Features**:
- Separated YouTube API (`YouTubeService`) and RSS (`RSSService`)
- Authentication handling
- Proper error handling

### `src/services/telegram_service.py`
**Purpose**: Telegram notification operations

**Key Features**:
- Clean message formatting
- Photo and text message support
- Centralized notification logic

### `src/services/firebase_service.py` (Enhanced)
**Purpose**: Complete state and data persistence

**Key Features**:
- All CRUD operations for channels and videos
- State management through Firebase
- Graceful degradation with NullFirebaseService
- Real-time data synchronization

### `src/services/bot_service.py`
**Purpose**: Main application orchestrator

**Key Features**:
- Dependency injection
- Background task management
- Clean error handling
- Business logic coordination
- **Firebase-first approach**: Requires Firebase to be available

## 🔄 Data Flow (Firebase-Only)

```
User Config → BotConfig → YouTubeBotService
                              ↓
┌─────────────────────────────────────────────────┐
│ YouTubeBotService (Orchestrator)                │
├─────────────────────────────────────────────────┤
│ ├── YouTubeService (API operations)             │
│ ├── RSSService (Feed parsing)                   │
│ ├── TelegramService (Notifications)             │
│ └── FirebaseService (ONLY persistence layer)    │
└─────────────────────────────────────────────────┘
                              ↓
    Video/Channel Models → Firebase Firestore → Notifications
                              ↓
┌─────────────────────────────────────────────────┐
│ Firebase Collections                            │
├─────────────────────────────────────────────────┤
│ ├── videos (all discovered videos)             │
│ ├── subscriptions (channel data & preferences) │
│ └── bot_state (sync timestamps)                │
└─────────────────────────────────────────────────┘
```

## 🧪 Testing Strategy

### Unit Testing
Each service can be tested in isolation:
- Mock dependencies using protocols
- Test individual methods
- Verify error handling

### Integration Testing
Test service interactions:
- State persistence
- API integrations
- End-to-end workflows

### Example Test Structure
```python
def test_video_processing():
    # Arrange
    mock_firebase = MockFirebaseService()
    mock_telegram = MockTelegramService()
    bot_service = YouTubeBotService(config, mock_firebase, mock_telegram)
    
    # Act
    bot_service.process_new_video(video)
    
    # Assert
    assert mock_firebase.save_video_called
    assert mock_telegram.send_notification_called
```

## 🚀 Benefits of This Architecture

### Maintainability
- **Clear boundaries**: Each module has a specific purpose
- **Easy to locate**: Business logic is organized logically
- **Consistent patterns**: Similar operations follow the same structure

### Testability
- **Dependency injection**: Easy to mock external dependencies
- **Isolated testing**: Each service can be tested independently
- **Protocol-based**: Interfaces make testing straightforward

### Extensibility
- **Plugin architecture**: New services can be added easily
- **Configuration-driven**: Behavior can be modified without code changes
- **Protocol compliance**: New implementations follow existing contracts

### Reliability
- **Error isolation**: Failures in one service don't crash others
- **Fail-fast principle**: Bot stops if Firebase is unavailable (by design)
- **Type safety**: Compile-time error detection
- **Cloud resilience**: Firebase handles availability and scaling

## 📝 Usage Examples

### Adding a New Notification Channel
```python
class DiscordService:
    def send_video_notification(self, video: Video) -> bool:
        # Implementation
        pass

# In bot_service.py
class YouTubeBotService:
    def __init__(self, config: BotConfig):
        self._discord_service = DiscordService(config.discord_token)
    
    def _process_new_video(self, channel: Channel, video: Video):
        # Send to multiple channels
        self._telegram_service.send_video_notification(video)
        self._discord_service.send_video_notification(video)
```

### Adding New Configuration
```python
@dataclass(frozen=True)
class BotConfig:
    # Existing fields...
    max_videos_per_hour: int = 10
    
    @classmethod
    def from_env(cls) -> "BotConfig":
        return cls(
            # ... existing fields
            max_videos_per_hour=int(os.getenv("MAX_VIDEOS_PER_HOUR", "10"))
        )
```

### Working with Firebase Collections
```python
# Get all channels with notification preferences
channels = firebase_service.get_all_channels()
for channel in channels:
    print(f"{channel.title}: notify={channel.notify}")

# Check if channel exists
if firebase_service.channel_exists("UC123"):
    channel = firebase_service.get_channel("UC123")

# Save new video
video = Video(video_id="abc123", title="Test", ...)
firebase_service.save_video(video)

# Update notification preferences
firebase_service.update_channel_notify_preference("UC123", False)
```

### Managing Notification Preferences
```python
# Toggle notifications for a channel
bot_service.toggle_channel_notifications("UC123456")

# Set specific notification preference
bot_service.set_channel_notifications("UC123456", False)

# The bot respects these preferences during video processing
# Videos are still saved to Firebase, but notifications are conditional
```

## 🔧 Migration from Original Code

The refactored code maintains the same functionality while providing:

1. **Better organization**: Code is logically grouped
2. **Improved testability**: Dependencies can be mocked
3. **Enhanced maintainability**: Changes are localized
4. **Type safety**: Better IDE support and error detection
5. **Documentation**: Clear interfaces and responsibilities
6. **Cloud-first storage**: No more local file management
7. **Simplified state**: Single source of truth in Firebase

### Running the Refactored Version
```bash
# Use the new main file
python main_refactored.py

# Or rename it to replace the original
mv main.py main_original.py
mv main_refactored.py main.py
```

## 🎯 Future Improvements

1. **Dependency Injection Container**: Use a DI framework for larger applications
2. **Event-Driven Architecture**: Implement pub/sub for loose coupling
3. **Multiple Cloud Providers**: Add support for other databases (maintaining Firebase-first)
4. **Metrics and Monitoring**: Add observability with structured logging
5. **API Layer**: Add REST API for external integrations
6. **Multi-Instance Support**: Leverage Firebase's real-time capabilities for coordination
7. **Firebase Security Rules**: Add proper access control for production use