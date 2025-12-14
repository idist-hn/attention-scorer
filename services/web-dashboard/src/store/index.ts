import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Auth Store
interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (user: User, token: string) => void;
  logout: () => void;
  updateUser: (user: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: (user, token) => set({ user, token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
      updateUser: (updates) => set((state) => ({
        user: state.user ? { ...state.user, ...updates } : null,
      })),
    }),
    { name: 'auth-storage' }
  )
);

// Meeting Store
interface Participant {
  id: string;
  name: string;
  avatar?: string;
  attention_score: number;
  is_looking_away: boolean;
  is_drowsy: boolean;
  is_active: boolean;
}

interface Meeting {
  id: string;
  title: string;
  status: 'scheduled' | 'active' | 'ended';
  host_id: string;
  start_time?: string;
  end_time?: string;
  participants: Participant[];
}

interface MeetingState {
  currentMeeting: Meeting | null;
  meetings: Meeting[];
  setCurrentMeeting: (meeting: Meeting | null) => void;
  setMeetings: (meetings: Meeting[]) => void;
  updateParticipant: (participantId: string, updates: Partial<Participant>) => void;
  addParticipant: (participant: Participant) => void;
  removeParticipant: (participantId: string) => void;
}

export const useMeetingStore = create<MeetingState>((set) => ({
  currentMeeting: null,
  meetings: [],
  setCurrentMeeting: (meeting) => set({ currentMeeting: meeting }),
  setMeetings: (meetings) => set({ meetings }),
  updateParticipant: (participantId, updates) => set((state) => {
    if (!state.currentMeeting) return state;
    return {
      currentMeeting: {
        ...state.currentMeeting,
        participants: state.currentMeeting.participants.map((p) =>
          p.id === participantId ? { ...p, ...updates } : p
        ),
      },
    };
  }),
  addParticipant: (participant) => set((state) => {
    if (!state.currentMeeting) return state;
    return {
      currentMeeting: {
        ...state.currentMeeting,
        participants: [...state.currentMeeting.participants, participant],
      },
    };
  }),
  removeParticipant: (participantId) => set((state) => {
    if (!state.currentMeeting) return state;
    return {
      currentMeeting: {
        ...state.currentMeeting,
        participants: state.currentMeeting.participants.filter(
          (p) => p.id !== participantId
        ),
      },
    };
  }),
}));

// Alert Store
interface Alert {
  id: string;
  participant_name: string;
  alert_type: 'not_attentive' | 'looking_away' | 'drowsy';
  severity: 'info' | 'warning' | 'critical';
  message: string;
  created_at: string;
  resolved_at?: string;
}

interface AlertState {
  alerts: Alert[];
  addAlert: (alert: Alert) => void;
  dismissAlert: (alertId: string) => void;
  clearAlerts: () => void;
}

export const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  addAlert: (alert) => set((state) => ({
    alerts: [alert, ...state.alerts].slice(0, 50), // Keep last 50
  })),
  dismissAlert: (alertId) => set((state) => ({
    alerts: state.alerts.filter((a) => a.id !== alertId),
  })),
  clearAlerts: () => set({ alerts: [] }),
}));

// Settings Store
interface SettingsState {
  theme: 'light' | 'dark' | 'system';
  notifications: boolean;
  alertSound: boolean;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
  setNotifications: (enabled: boolean) => void;
  setAlertSound: (enabled: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      theme: 'system',
      notifications: true,
      alertSound: true,
      setTheme: (theme) => set({ theme }),
      setNotifications: (notifications) => set({ notifications }),
      setAlertSound: (alertSound) => set({ alertSound }),
    }),
    { name: 'settings-storage' }
  )
);

