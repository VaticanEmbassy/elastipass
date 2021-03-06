<template>
  <div id="search" class="search">
    <h1>Elastipass</h1>
    Search for emails, passwords and domains.
    <p>
    <br />
    <strong>NOTICE: DO NOT MISUSE THESE DATA.  Do not scrape the whole db doing queries on it. Keep in mind that the first goal is to allow people to do analyses on the passwords. Also, notice that all of the data is from sources that are publicly available since many years, and for the most part are obsolete.</strong>
    </p>

    <pacman-loader :loading="loading" class="pacman"></pacman-loader>

    <div style="margin-top: 15px;">
        <el-input placeholder="query" v-model="query" @keyup.enter.native="submitQuery()" class="queryInput">
            <el-select v-model="searchType" slot="prepend" class="searchTypeSelect" >
                <el-option label="email, exact" value="term:email.raw"></el-option>
                <el-option label="smart" value="default"></el-option>
                <el-option label="username, exact" value="term:username.raw"></el-option>
                <el-option label="email, match" value="match:email"></el-option>
                <el-option label="domain, exact" value="term:domain"></el-option>
                <el-option label="domain (no TLD), exact" value="term:domain_notld"></el-option>
                <el-option label="password, exact" value="term:password.raw"></el-option>
            </el-select>
            <el-select v-model="searchIndices" slot="append" class="searchIndicesSelect" >
                <el-option label="all" value="all"></el-option>
                <el-option label="classic" value="classic"></el-option>
                <el-option label="pastebin" value="pastebin"></el-option>
            </el-select>
        </el-input>
        <el-button icon="search" @click="submitQuery()"></el-button>
    </div>

    <br />
    <v-server-table ref="dataTable" url="/api" :columns="tableColumns" :options="tableOptions" @loaded="onTableLoaded"></v-server-table>

      <div>
          The number of results can be approximated.<br/>
          The Elasticsearch schema is more or less <a href="/static/elastic_schema.json" download>this one</a>.

          <br />
          The available dumps are <a href="/static/dumps.txt" target="_blank">these ones</a>; the data is NOT deduplicated.<br />
          Currently there are <b>over 2.68 billion entries</b>.
          <br />
          <br />
           The database is continuously updated using a feed from <b>pastebin</b>.

          <h2>GUI</h2>
          You can run various kind of queries using this GUI. The <strong>smart</strong> query is something like &quot;(term:email.raw * 3 boost) + (term:username.raw * 2 boost) + match:username&quot;; it - and the "match" query - can be somehow heavy, so use them only if needed.

          <h2>Analyses</h2>
          We have analyzed some data; the raw results <a href="/static/index.html">can be found here</a>.
          Besides some global stats, we have extracted the most used passwords for many TLD and their most popular domains.

          <h2>API</h2>
          You can also directly access the <strong>/api</strong> endpoint, with the following arguments:
          <ul>
              <li><strong>q</strong>: the query; for example, your own email address</li>
              <li><strong>kind</strong>: the type of query; can be one of: term, match, fuzzy, regexp, ...</li>
              <li><strong>field</strong>: the field to match; one of: email, username, username.raw, password, ...</li>
              <li><strong>offset</strong>: an integer representing the start entry</li>
              <li><strong>limit</strong>: how many results are returned, at most</li>
          </ul>

          <h4>Direct query</h4>
          The <strong>/api</strong> endpoint can also be called directly with a full Elasticsearch query, without the need to specify any of the above parameters; if you need to familiarize with Elasticsearch, start with the <a href="https://www.elastic.co/guide/en/elasticsearch/guide/current/query-dsl-intro.html" target="_blank">official documentation</a>.

          The data is split in multiple indices, named <b>pwd_*</b>  Live data is stored in the <b>pastebin_*</b> indices.
          <p>
          Please avoid doing damage to the database or queries that takes too long.

          <h2>Import process</h2>
          We used <a href="https://github.com/VaticanEmbassy/golastipass">golastipass</a> to import the data in Elasticsearch.

          <h2>Contacts</h2>
          <a href="mailto:pwdmonk3ys@esiliati.org">Write us a mail</a>.
      </div>
  </div>
</template>

<script>

import PacmanLoader from 'vue-spinner/src/PacmanLoader.vue';

export default {
    name: 'Search',
    data () {
        return {
            query: '',
            previousQuery: '',
            searchType: 'term:email.raw',
            previousSearchType: 'term:email.raw',
            searchIndices: 'all',
            previousSearchIndices: 'all',
            data: [],
            nolog: false,
            loading: false,
            tableColumns: ["email", "password"],
            tableOptions: {
                clientMultiSorting: false,
                filterable: false,
                requestKeys: {
                    query: 'q',
                    orderBy: '',
                    ascending: '',
                    byColumn: ''
                },
                responseAdapter: function(resp) {
                    return {
                        data: resp.results,
                        count: resp.total
                    };
                },
                requestFunction: function(data) {
                        // this will throw a "TypeError: Cannot read property 'then' of undefined"
                        //return;
                    if (data[''] !== undefined) {
                        delete data[''];
                    }
                    if (data.q.kind) {
                        data.kind = data.q.kind;
                    }
                    if (data.q.field) {
                        data.field = data.q.field;
                    }
                    if (data.q.indices) {
                        data.indices = data.q.indices;
                    }
                    if (data.q.page !== undefined) {
                        data.page = data.q.page;
                    }
                    if(window.globalVue && window.globalVue._route && window.globalVue._route.query && window.globalVue._route.query.nolog) {
                        data.nolog = true;
                    }

                    data.q = data.q.query;
                    return axios.get(this.url, {params: data}).catch(
                        function (e) {
                            this.dispatch('error', e);
                        }.bind(this)
                    );
                },
                perPageValues: [10, 25, 50, 100, 200],
                sortable: []
            }
        }
    },

    mounted: function() {
        var route = this.$router.currentRoute;
        if (!(route.name == 'search' && route.query && route.query.query)) {
            return;
        }
        this.query = route.query.query;
        if (route.query.nolog) {
            this.nolog = true;
        }
        var kindAndField = route.query.kind || '';
        if (kindAndField && route.query.field) {
            kindAndField = kindAndField + ':' + route.query.field;
        }
        if (this.kindAndField) {
            this.searchType = kindAndField;
        }
        this.searchIndices = route.query.indices || 'all';
        // that's so wrong it hurts, but it's needed to avoid that the call is overwritten
        // by the first call made by v-server-table to /api.
        setTimeout(this.submitQuery, 400);
    },

    methods: {
        onTableLoaded() {
            this.loading = false;
        },

        submitQuery(noPathUpdate) {
            if (!this.query) {
                return;
            }
            var args = {query: this.query, indices: this.searchIndices};
            var kindAndField = this.searchType.split(':', 2);
            args.kind = kindAndField[0];
            if (kindAndField.length == 2) {
                args.field = kindAndField[1];
            }
            if (this.nolog) {
                args.nolog = true;
            }
            this.$router.push({
                path: '/',
                query: args
            });
            document.title = this.query || '';
            if (this.query != this.previousQuery ||
                    this.searchType != this.previousSearchType ||
                    this.searchIndices != this.previousSearchIndices) {
                this.loading = true;
                this.$refs.dataTable.setFilter(args);
                if (this.$refs.dataTable.page != 1) {
                    this.$refs.dataTable.setPage(1);
                }
            }
            this.previousQuery = this.query;
            this.previousSearchType = this.searchType;
            this.previousSearchIndices = this.searchIndices;
        }
    },
    components: { PacmanLoader }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>

.VueTables {
    max-width: 80%;
}

.search {
    margin: 12px;
}

h1, h2 {
  font-weight: normal;
}

ul {
  list-style-type: none;
  padding: 0;
}

li {
  display: inline-block;
  margin: 0 10px;
}

a {
  color: #42b983;
}


.el-select .el-input {
    width: 110px;
}

li {
    display: block;
}

.queryInput {
    max-width: 800px;
}

.searchTypeSelect {
    min-width: 200px;
}

.searchIndicesSelect {
    min-width: 100px;
}

.pacman {
    position: absolute !important;
    top: 30%;
    left: 50%;
}

</style>
