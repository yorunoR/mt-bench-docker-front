<template>
  <div class="p-1">
    <router-view />
  </div>
  <Toast :breakpoints="{ '576px': { width: '97%', left: '6px' } }" />
</template>

<script setup lang="ts">
import { provideClient } from '@urql/vue'

import { makeClient } from '@/services/client'

provideClient(makeClient())
</script>
