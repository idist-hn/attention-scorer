'use client';

import React from 'react';
import Link from 'next/link';
import { ArrowLeft, Moon, Sun, Bell, Volume2, Monitor } from 'lucide-react';
import { useSettingsStore } from '@/store';

export default function SettingsPage() {
  const { theme, notifications, alertSound, setTheme, setNotifications, setAlertSound } = useSettingsStore();

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 shadow">
        <div className="container mx-auto px-4 py-4 flex items-center gap-4">
          <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Settings</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-6 max-w-2xl">
        {/* Appearance */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6">
          <div className="p-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Appearance</h2>
          </div>
          <div className="p-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
              Theme
            </label>
            <div className="flex gap-2">
              <ThemeButton
                icon={<Sun className="w-5 h-5" />}
                label="Light"
                active={theme === 'light'}
                onClick={() => setTheme('light')}
              />
              <ThemeButton
                icon={<Moon className="w-5 h-5" />}
                label="Dark"
                active={theme === 'dark'}
                onClick={() => setTheme('dark')}
              />
              <ThemeButton
                icon={<Monitor className="w-5 h-5" />}
                label="System"
                active={theme === 'system'}
                onClick={() => setTheme('system')}
              />
            </div>
          </div>
        </section>

        {/* Notifications */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow mb-6">
          <div className="p-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Notifications</h2>
          </div>
          <div className="p-4 space-y-4">
            <ToggleSetting
              icon={<Bell className="w-5 h-5" />}
              label="Push Notifications"
              description="Receive notifications for alerts and updates"
              enabled={notifications}
              onChange={setNotifications}
            />
            <ToggleSetting
              icon={<Volume2 className="w-5 h-5" />}
              label="Alert Sound"
              description="Play sound when critical alerts occur"
              enabled={alertSound}
              onChange={setAlertSound}
            />
          </div>
        </section>

        {/* About */}
        <section className="bg-white dark:bg-gray-800 rounded-lg shadow">
          <div className="p-4 border-b dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">About</h2>
          </div>
          <div className="p-4">
            <div className="flex justify-between py-2">
              <span className="text-gray-500">Version</span>
              <span className="text-gray-900 dark:text-white">1.0.0</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-gray-500">Build</span>
              <span className="text-gray-900 dark:text-white">2024.01.15</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function ThemeButton({ icon, label, active, onClick }: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex-1 flex items-center justify-center gap-2 py-3 px-4 rounded-lg border-2 transition-colors ${
        active
          ? 'border-blue-500 bg-blue-50 text-blue-600 dark:bg-blue-900/20'
          : 'border-gray-200 dark:border-gray-600 hover:border-gray-300'
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ToggleSetting({ icon, label, description, enabled, onChange }: {
  icon: React.ReactNode;
  label: string;
  description: string;
  enabled: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="text-gray-400">{icon}</div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{label}</p>
          <p className="text-sm text-gray-500">{description}</p>
        </div>
      </div>
      <button
        onClick={() => onChange(!enabled)}
        className={`relative w-12 h-6 rounded-full transition-colors ${
          enabled ? 'bg-blue-600' : 'bg-gray-300 dark:bg-gray-600'
        }`}
      >
        <span
          className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
            enabled ? 'translate-x-7' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

