<script setup lang="ts">
import Navbar from '@/components/Navbar.vue'
</script>

<template>
  <div id="app">
    <Navbar />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<style>
#app {
  min-height: 100vh;
}

.main-content {
  padding-top: 64px;
  background-color: var(--bg-color);
  min-height: calc(100vh - 64px);
}
</style>
