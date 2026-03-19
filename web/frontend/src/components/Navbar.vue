<script setup lang="ts">
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const navLinks = [
  { path: '/', label: '起卦' },
  { path: '/history', label: '历史' }
]
</script>

<template>
  <nav class="navbar">
    <!-- Logo -->
    <RouterLink to="/" class="logo">
      <div class="logo-icon">☯</div>
      <span class="logo-text">易策</span>
    </RouterLink>

    <!-- Navigation Links -->
    <ul class="nav-links">
      <li v-for="link in navLinks" :key="link.path">
        <RouterLink
          :to="link.path"
          class="nav-link"
          :class="{ active: route.path === link.path }"
        >
          {{ link.label }}
        </RouterLink>
      </li>
    </ul>

    <!-- Settings Button -->
    <RouterLink to="/settings" class="settings-btn" aria-label="设置">
      <svg
        class="settings-icon"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="12" cy="12" r="3" />
        <path
          d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"
        />
      </svg>
    </RouterLink>
  </nav>
</template>

<style scoped>
/* CSS Variables */
:root {
  --navbar-bg: var(--bg-color, #000000);
  --navbar-border: rgba(255, 255, 255, 0.1);
  --navbar-text: var(--text-secondary, rgba(255, 255, 255, 0.6));
  --navbar-text-active: var(--yang-color, #ffd700);
  --navbar-logo-border: var(--yang-color, #ffd700);
  --navbar-transition: color 0.3s ease, border-color 0.3s ease, background-color 0.3s ease;
}

.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 40px;
  background-color: var(--navbar-bg);
  border-bottom: 1px solid var(--navbar-border);
  z-index: 100;
}

/* Logo */
.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  text-decoration: none;
  transition: var(--navbar-transition);
}

.logo-icon {
  width: 36px;
  height: 36px;
  border: 2px solid var(--navbar-logo-border);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--navbar-logo-border);
  transition: var(--navbar-transition);
}

.logo:hover .logo-icon {
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.4);
}

.logo-text {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 4px;
  color: var(--text-primary, #ffffff);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
}

/* Navigation Links */
.nav-links {
  display: flex;
  gap: 40px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.nav-link {
  color: var(--navbar-text);
  text-decoration: none;
  font-size: 16px;
  letter-spacing: 2px;
  transition: var(--navbar-transition);
  font-family: "Noto Serif SC", "Songti SC", "SimSun", serif;
  position: relative;
}

.nav-link:hover {
  color: var(--navbar-text-active);
}

.nav-link.active {
  color: var(--navbar-text-active);
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: -4px;
  left: 0;
  right: 0;
  height: 2px;
  background-color: var(--navbar-text-active);
  border-radius: 1px;
}

/* Settings Button */
.settings-btn {
  width: 40px;
  height: 40px;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  background: transparent;
  color: var(--navbar-text);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  transition: var(--navbar-transition);
}

.settings-btn:hover {
  border-color: var(--navbar-text-active);
  color: var(--navbar-text-active);
  box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
}

.settings-btn.router-link-active {
  border-color: var(--navbar-text-active);
  color: var(--navbar-text-active);
}

.settings-icon {
  width: 20px;
  height: 20px;
}

/* Responsive - Desktop first */
@media (max-width: 768px) {
  .navbar {
    padding: 16px 24px;
  }

  .logo-text {
    font-size: 20px;
    letter-spacing: 3px;
  }

  .nav-links {
    gap: 24px;
  }

  .nav-link {
    font-size: 14px;
    letter-spacing: 1px;
  }
}
</style>
