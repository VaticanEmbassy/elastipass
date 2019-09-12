// The Vue build version to load with the `import` command
// (runtime-only or standalone) has been set in webpack.base.conf with an alias.
import Vue from 'vue';
import ElementUI from 'element-ui';
import 'element-ui/lib/theme-default/index.css';
require('../node_modules/bootstrap/less/bootstrap.less');
import Search from './components/Search';
import App from './App';
import VueRouter from 'vue-router';
window.axios = require('axios');
import {ServerTable, ClientTable, Event} from 'vue-tables-2';
import PulseLoader from 'vue-spinner/src/PulseLoader.vue'


Vue.config.productionTip = false;
Vue.use(VueRouter);
Vue.use(ElementUI);
Vue.use(ServerTable);
Vue.use(PulseLoader);

var routes = [
    {path: '/', name: 'search', component: App}
];

const router = new VueRouter({routes});

/* eslint-disable no-new */
window.globalVue = new Vue({
  el: '#app',
  router: router,
  template: '<div><Search/></div>',
  components: { App, Search }
});
