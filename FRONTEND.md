# Frontend Specification for YouTube Video Bot

This document outlines the requirements and specifications for building a web-based frontend to manage the YouTube Video Bot.

## 🎯 Overview

The frontend should provide a user-friendly interface to:
- View and manage YouTube channel subscriptions
- Control notification preferences per channel
- Monitor recent video discoveries
- Configure bot settings
- View system status and logs

## 🏗️ Architecture Requirements

### Technology Stack Recommendations
- **Framework**: React.js, Vue.js, or Angular
- **State Management**: Redux/Zustand (React), Vuex (Vue), or NgRx (Angular)
- **UI Library**: Material-UI, Ant Design, or Tailwind CSS
- **Backend Integration**: REST API or GraphQL
- **Real-time Updates**: WebSocket or Server-Sent Events
- **Authentication**: Firebase Auth or custom JWT

### Backend API Requirements
The frontend will need a REST API or GraphQL endpoint to interact with the bot's Firebase data.

## 📱 Core Features

### 1. Dashboard (Home Page)
**Purpose**: Overview of bot status and recent activity

**Components**:
- Bot status indicator (running/stopped/error)
- Statistics cards:
  - Total subscribed channels
  - Videos discovered today/this week
  - Notifications sent today
  - Channels with notifications disabled
- Recent video feed (last 20 videos)
- Quick actions panel

**Data Requirements**:
```typescript
interface DashboardData {
  botStatus: 'running' | 'stopped' | 'error'
  stats: {
    totalChannels: number
    videosToday: number
    videosThisWeek: number
    notificationsSent: number
    channelsWithNotificationsDisabled: number
  }
  recentVideos: Video[]
  lastSyncTime: string
}
```

### 2. Channel Management
**Purpose**: View and manage YouTube channel subscriptions

**Components**:
- Channel list with search and filter
- Notification toggle per channel
- Channel details modal
- Bulk actions (enable/disable notifications)
- Add new channel (if needed)

**Features**:
- **Search**: Filter channels by name
- **Filter**: Show all, notifications on, notifications off
- **Sort**: By name, subscription date, last video
- **Actions**: Toggle notifications, view channel details

**Data Requirements**:
```typescript
interface Channel {
  channel_id: string
  title: string
  thumbnail?: string
  subscriber_count?: string
  last_video_id: string
  last_video_title?: string
  last_video_date?: string
  notify: boolean
  subscribed_at: string
  last_updated: string
  rss_url: string
}

interface ChannelListProps {
  channels: Channel[]
  onToggleNotification: (channelId: string) => void
  onBulkToggle: (channelIds: string[], notify: boolean) => void
  searchTerm: string
  filter: 'all' | 'notify-on' | 'notify-off'
}
```

### 3. Video History
**Purpose**: Browse discovered videos with filtering and search

**Components**:
- Video grid/list view
- Date range picker
- Channel filter
- Search by video title
- Video details modal

**Features**:
- **Timeline**: View videos by date range
- **Channel Filter**: Show videos from specific channels
- **Search**: Find videos by title or description
- **Actions**: Open in YouTube, mark as seen

**Data Requirements**:
```typescript
interface Video {
  video_id: string
  title: string
  channel_id: string
  channel_title: string
  link: string
  thumbnail?: string
  discovered_at: string
  published_at?: string
  description?: string
}

interface VideoHistoryProps {
  videos: Video[]
  dateRange: { start: Date; end: Date }
  selectedChannels: string[]
  searchTerm: string
  onDateRangeChange: (range: { start: Date; end: Date }) => void
}
```

### 4. Settings Page
**Purpose**: Configure bot settings and preferences

**Components**:
- Bot configuration form
- Firebase connection status
- Telegram settings
- Export/import settings
- System logs viewer

**Settings Categories**:
```typescript
interface BotSettings {
  telegram: {
    botToken: string
    chatId: string
  }
  youtube: {
    clientSecretFile: string
    tokenFile: string
  }
  firebase: {
    credentialsFile: string
    projectId: string
  }
  polling: {
    videoCheckIntervalSeconds: number
    subscriptionSyncIntervalMinutes: number
  }
  notifications: {
    initMode: boolean
    globalNotificationsEnabled: boolean
  }
}
```

### 5. Notification Center
**Purpose**: Manage notification preferences and history

**Components**:
- Global notification toggle
- Per-channel notification matrix
- Notification history
- Test notification feature

**Features**:
- **Quick Toggle**: Enable/disable all notifications
- **Channel Matrix**: Grid view of all channels with toggle switches
- **History**: Log of sent notifications
- **Testing**: Send test notification to verify setup

## 🔌 API Endpoints

### Authentication
```typescript
POST /api/auth/login
POST /api/auth/logout
GET /api/auth/status
```

### Dashboard
```typescript
GET /api/dashboard/stats
GET /api/dashboard/recent-videos
GET /api/bot/status
```

### Channels
```typescript
GET /api/channels
GET /api/channels/:id
PUT /api/channels/:id/notify
POST /api/channels/bulk-notify
DELETE /api/channels/:id
```

### Videos
```typescript
GET /api/videos
GET /api/videos/search
GET /api/videos/by-channel/:channelId
```

### Settings
```typescript
GET /api/settings
PUT /api/settings
POST /api/settings/test-notification
GET /api/system/logs
```

### Real-time Updates
```typescript
WebSocket /api/ws/updates
// Events: new-video, channel-updated, bot-status-changed, notification-sent
```

## 🎨 UI/UX Design Guidelines

### Visual Design
- **Theme**: Dark and light mode support
- **Colors**: YouTube-inspired red accent with neutral grays
- **Typography**: Clean, readable fonts (Inter, Roboto, or system fonts)
- **Icons**: Material Icons or Feather icons for consistency

### Layout
- **Responsive**: Mobile-first design with tablet and desktop breakpoints
- **Navigation**: Side navigation for desktop, bottom tabs for mobile
- **Cards**: Use card-based layout for channels and videos
- **Tables**: For detailed data views with sorting and filtering

### User Experience
- **Loading States**: Skeleton screens and progress indicators
- **Error Handling**: Toast notifications and error boundaries
- **Accessibility**: ARIA labels, keyboard navigation, screen reader support
- **Performance**: Virtual scrolling for large lists, lazy loading

## 📊 State Management

### Global State Structure
```typescript
interface AppState {
  auth: {
    user: User | null
    isAuthenticated: boolean
    loading: boolean
  }
  bot: {
    status: 'running' | 'stopped' | 'error'
    lastSync: string
    stats: DashboardStats
  }
  channels: {
    items: Channel[]
    loading: boolean
    searchTerm: string
    filter: string
    sortBy: string
  }
  videos: {
    items: Video[]
    loading: boolean
    dateRange: DateRange
    selectedChannels: string[]
  }
  settings: {
    config: BotSettings
    loading: boolean
    unsavedChanges: boolean
  }
  notifications: {
    toasts: Toast[]
    unreadCount: number
  }
}
```

## 🔐 Security Considerations

### Authentication
- Secure login system (Firebase Auth recommended)
- JWT tokens with proper expiration
- CSRF protection
- Rate limiting on API endpoints

### Data Protection
- Environment variables for sensitive data
- Encrypted storage for API keys
- HTTPS enforcement
- Input validation and sanitization

## 📱 Mobile Responsiveness

### Breakpoints
- Mobile: 320px - 768px
- Tablet: 768px - 1024px
- Desktop: 1024px+

### Mobile-Specific Features
- Touch-friendly interface
- Swipe gestures for actions
- Bottom sheet modals
- Simplified navigation
- Offline capability (view cached data)

## 🚀 Performance Requirements

### Loading Times
- Initial page load: < 3 seconds
- Navigation between pages: < 1 second
- Data fetching: < 2 seconds
- Real-time updates: < 500ms

### Optimization Techniques
- Code splitting and lazy loading
- Image optimization and lazy loading
- Virtual scrolling for large lists
- Caching with service workers
- Bundle size optimization

## 🧪 Testing Strategy

### Frontend Testing
```typescript
// Component tests
describe('ChannelList', () => {
  it('should toggle notifications when clicked', () => {
    // Test implementation
  })
})

// Integration tests
describe('Channel Management Flow', () => {
  it('should update notification preference in Firebase', () => {
    // Test implementation
  })
})

// E2E tests
describe('User Workflow', () => {
  it('should complete full channel management workflow', () => {
    // Cypress or Playwright test
  })
})
```

## 🔄 Real-time Features

### WebSocket Events
```typescript
interface WebSocketEvents {
  'new-video': { video: Video; channel: Channel }
  'channel-updated': { channel: Channel }
  'bot-status-changed': { status: BotStatus }
  'notification-sent': { video: Video; channel: Channel; timestamp: string }
  'sync-completed': { channelCount: number; newVideos: number }
}
```

### Live Updates
- Real-time video feed updates
- Live bot status indicator
- Instant notification preference changes
- Live statistics updates

## 📁 Project Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── common/
│   │   ├── dashboard/
│   │   ├── channels/
│   │   ├── videos/
│   │   ├── settings/
│   │   └── layout/
│   ├── pages/
│   ├── services/
│   │   ├── api.ts
│   │   ├── websocket.ts
│   │   └── firebase.ts
│   ├── store/
│   ├── types/
│   ├── utils/
│   └── hooks/
├── tests/
└── docs/
```

## 🎯 MVP Features (Phase 1)

1. **Dashboard**: Basic stats and recent videos
2. **Channel List**: View channels with notification toggles
3. **Video History**: Simple list view with search
4. **Settings**: Basic bot configuration
5. **Authentication**: Simple login system

## 🚀 Advanced Features (Phase 2)

1. **Analytics**: Charts and detailed statistics
2. **Notification Scheduling**: Time-based notification rules
3. **Custom Filters**: Advanced video filtering options
4. **Export Features**: Data export capabilities
5. **Multi-bot Support**: Manage multiple bot instances

## 🔧 Development Setup

### Prerequisites
- Node.js 18+
- Firebase project setup
- Bot backend running
- Environment variables configured

### Installation
```bash
npm create react-app youtube-bot-frontend --template typescript
cd youtube-bot-frontend
npm install @mui/material @emotion/react @emotion/styled
npm install firebase axios react-router-dom
npm start
```

## 📝 Implementation Notes

1. **Firebase Integration**: Use Firebase SDK directly or create API layer
2. **Real-time Updates**: WebSocket connection or Firebase real-time listeners
3. **State Persistence**: Use localStorage for user preferences
4. **Error Handling**: Comprehensive error boundaries and user feedback
5. **Accessibility**: Follow WCAG 2.1 guidelines
6. **Internationalization**: Prepare for multi-language support

This frontend specification provides a comprehensive foundation for building a professional web interface to manage the YouTube Video Bot with notification preferences and real-time capabilities.