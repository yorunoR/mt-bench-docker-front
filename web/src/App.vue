<template>
  <RouterView />
</template>

<style>
html,
body {
  box-sizing: border-box;
  height: 100%;
  margin: 0px;
  font-size: 14px;
}

#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #5a5a72;
  background-color: white;
  min-height: 100%;
}

a {
  color: #2c3e50;
}

a.router-link-exact-active {
  color: #42b983;
}
</style>
