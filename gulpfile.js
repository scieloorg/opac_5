'use strict';

const { src, dest, watch, series, parallel } = require('gulp');
const path = require('path');
const less = require('gulp-less');
const sass = require('gulp-sass')(require('sass'));
const cleanCSS = require('gulp-clean-css');
const uglify = require('gulp-uglify');
const sourceMaps = require('gulp-sourcemaps');
const connect = require('gulp-connect');
const gutil = require('gulp-util');
const rename = require('gulp-rename');
const concat = require('gulp-concat');
const minifyCSS = require('gulp-minify-css');
const stripDebug = require('gulp-strip-debug');
const include = require('gulp-include');


let node_folder_path_bootstrap = path.join(__dirname, 'node_modules/bootstrap');

// caminho da pasta 'node_modules/bootstrap'
let node_folder_path = path.join(__dirname, 'node_modules/');
console.info('[INFO] [gulpfile.js] path da pasta node_modules:\t', node_folder_path);

// caminho da pasta 'node_modules/scielo-design-system/src/bootstrap/scss'
let node_folder_path_scielo_ds = path.join(__dirname, 'node_modules/scielo-design-system/src/bootstrap/scss/');
console.info('[INFO] [gulpfile.js] path da pasta node_modules/scielo-design-system/src/bootstrap/scss:\t', node_folder_path_scielo_ds);

// caminho da pasta 'node_modules/scielo-design-system/dist/img'
let node_folder_path_scielo_ds_img = path.join(__dirname, 'node_modules/scielo-design-system/dist/img/');
console.info('[INFO] [gulpfile.js] path da pasta node_modules/scielo-design-system/dist/img:\t', node_folder_path_scielo_ds_img);

// caminho da pasta 'opac/webapp/static/'
let static_folder_path = path.join(__dirname, 'opac/webapp/static/');
console.info('[INFO] [gulpfile.js] path da pasta static:\t', static_folder_path);

let paths = {

    
    // caminho relativo da pasta 'bootstrap/js/ dentro do node_modules, fora do projeto'
    'bootstrap_js': path.join(node_folder_path, 'bootstrap/dist/js/'),
    // caminho relativo da pasta 'scielo-design-system/dist/js/bootstrap.min.js dentro do node_modules, fora do projeto'
    'scielo_design_system_bootstrap_js': path.join(node_folder_path, 'scielo-design-system/dist/js/'),
    // caminho relativo da pasta 'jquery/dist/ dentro do node_modules, fora do projeto'
    'jquery_js': path.join(node_folder_path, 'jquery/dist/'),
    // caminho relativo da pasta 'jquery-typeahead/dist/ dentro do node_modules, fora do projeto'
    'jquery-typeahead_js': path.join(node_folder_path, 'jquery-typeahead/dist/'),

    // caminho relativo da pasta 'static/js/'
    'static_js': path.join(static_folder_path, 'js/'),
    // caminho relativo da pasta 'static/less/'
    'static_less': path.join(static_folder_path, 'less/'),
    // caminho relativo da pasta 'static/sass/'
    'static_sass': path.join(static_folder_path, 'sass/'),
    // caminho relativo da pasta 'static/css/'
    'static_css': path.join(static_folder_path, 'css/'),
    // caminho relativo da pasta 'static/img/'
    'static_img': path.join(static_folder_path, 'img/'),
};

console.info('[INFO] [gulpfile.js] path da pasta bootstrap/js:\t', paths['bootstrap_js']);
//console.info('[INFO] [gulpfile.js] path da pasta bootstrap/less:\t', paths['bootstrap_less']);
//console.info('[INFO] [gulpfile.js] path da pasta bootstrap/css:\t', paths['bootstrap_css']);

console.info('[INFO] [gulpfile.js] path da pasta static/js:\t', paths['static_js']);
console.info('[INFO] [gulpfile.js] path da pasta static/less:\t', paths['static_less']);
console.info('[INFO] [gulpfile.js] path da pasta static/css:\t', paths['static_css']);

let target_src = {
    'js': {
        'scielo-bundle': [
            // instruções JS (designer)
            path.join(paths['jquery_js'], 'jquery.js'),                                     // foi setado para carregar separadamente
            path.join(paths['scielo_design_system_bootstrap_js'], 'bootstrap.bundle.js'),   // foi setado para carregar separadamente
            path.join(paths['jquery-typeahead_js'], 'jquery.typeahead.min.js'),
            path.join(paths['static_js'], 'plugins.js'),
            path.join(paths['static_js'], 'slick.min.js'),
            path.join(paths['static_js'], 'main.js'),
            path.join(paths['static_js'], 'cookieMsg.js'),
           
            // instruções JS (equipe scielo)
            path.join(paths['static_js'], 'common.js'),
            path.join(paths['static_js'], 'moment.js'),
            path.join(paths['static_js'], 'moment_locale_pt_br.js'),
            path.join(paths['static_js'], 'moment_locale_es.js'),
            path.join(paths['static_js'], 'modal_forms.js'),
        ],
        'scielo-article': [
            path.join(paths['static_js'], 'scielo-article.js'),
            path.join(paths['static_js'], 'scielo-article-floating-menu.js')

        ],
        'scielo-article-standalone': [
            path.join(paths['jquery_js'], 'jquery.js'),
            path.join(paths['scielo_design_system_bootstrap_js'], 'bootstrap.bundle.js'),
            path.join(paths['static_js'], 'plugins.js'),
            path.join(paths['static_js'], 'scielo-article.js'),
        ],
    },
    'less': {
        'scielo-bundle': [

            //path.join(node_folder_path, 'scielo-design-system/dist/css/bootstrap.css'),
            //path.join(paths['static_less'], 'scielo-bundle.less'),

            path.join(paths['static_less'], 'bootstrap.less'),
            path.join(paths['static_less'], 'scielo-portal.less'),
            path.join(paths['static_less'], 'collection.less'),
            path.join(paths['static_less'], 'journal-menu.less'),
            path.join(paths['static_less'], 'journal.less'),
            path.join(paths['static_less'], 'portal.less'),
            path.join(paths['static_less'], 'search.less'),

            path.join(paths['static_less'], 'style.less'),
            path.join(paths['static_less'], 'jquery.typeahead.less')
        ],
        'scielo-article': [
            path.join(paths['static_less'], 'scielo-article.less')
        ],
        'bootstrap': [
            path.join(paths['static_less'], 'bootstrap.less')
            //path.join(node_folder_path, 'scielo-design-system/css/bootstrap.css')
            //'bootstrap_js': path.join(node_folder_path, 'bootstrap/dist/js/'),
        ],
        'scielo-article-standalone': [
            path.join(paths['static_less'], 'scielo-article-standalone.less')
        ],
        'scielo-bundle-print': [
            path.join(paths['static_less'], 'scielo-bundle-print.less')
        ],
    },
    'sass': {
        'scielo-bundle': [
            path.join(paths['static_sass'], 'bootstrap.scss'),
            path.join(paths['static_sass'], 'scielo-portal.scss'),
            path.join(paths['static_sass'], 'collection.scss'),
            path.join(paths['static_sass'], 'journal-menu.scss'),
            path.join(paths['static_sass'], 'journal.scss'),
            path.join(paths['static_sass'], 'portal.scss'),
            path.join(paths['static_sass'], 'search.scss'),

            path.join(paths['static_sass'], 'style.scss'),
            path.join(paths['static_sass'], 'jquery.typeahead.scss')
        ],
        'scielo-article': [
            path.join(paths['static_sass'], 'scielo-article.scss')
        ],
        'bootstrap': [
            path.join(paths['static_sass'], 'bootstrap.scss')
        ],
        'scielo-article-standalone': [
            path.join(paths['static_sass'], 'scielo-article-standalone.scss')
        ],
        'scielo-bundle-print': [
            path.join(paths['static_sass'], 'scielo-bundle-print.scss')
        ],
    },
    'img': {
        'logos': [
            path.join(node_folder_path_scielo_ds_img, 'logo-scielo-no-label.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-scielo-no-label-negative.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-open-access.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-fapesp.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-fap.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-cnpq.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-capes.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-bvs.svg'),
            path.join(node_folder_path_scielo_ds_img, 'logo-footer-bireme.svg'),
        ]
    }
};

let output = {
    'js': {
        'folder': paths['static_js'],
        // caminho dos arquivos JS para salvar os resultados
        'scielo-bundle': 'scielo-bundle-min.js',
        'scielo-article': 'scielo-article-min.js',
        'scielo-article-standalone': 'scielo-article-standalone-min.js',
    },
    'css': { // caminho dos arquivos CSS para salvar os resultados
        'folder': paths['static_css'],
        'scielo-bundle': 'scielo-bundle.css',
        'scielo-article': 'scielo-article.css',
        'scielo-article-standalone': 'scielo-article-standalone.css',
        'scielo-bundle-print': 'scielo-bundle-print.css',
    },
    'img': { // caminho dos arquivos IMG SVG para salvar os resultados
        'folder': paths['static_img'],
        'logo-scielo-no-label': 'logo-scielo-no-label.svg',
        'logo-scielo-no-label-negative': 'logo-scielo-no-label-negative.svg',
        'logo-open-access':  'logo-open-access.svg',
        'logo-footer-fapesp':  'logo-footer-fapesp.svg',
        'logo-footer-fap':  'logo-footer-fap.svg',
        'logo-footer-cnpq':  'logo-footer-cnpq.svg',
        'logo-footer-capes':  'logo-footer-capes.svg',
        'logo-footer-bvs':  'logo-footer-bvs.svg',
        'logo-footer-bireme':  'logo-footer-bireme.svg'
    }
};

// Task para gerar o scielo-article-standalone.js
function processScieloArticleStandaloneJs(){
    return src(target_src['js']['scielo-article-standalone'])
    .pipe(concat(output['js']['scielo-article-standalone']))
    .pipe(sourceMaps.init())
    .pipe(stripDebug())
    .pipe(uglify())
    .pipe(sourceMaps.write('../maps'))
    .pipe(dest(output['js']['folder']));
}

// Task para gerar o scielo-article.js
function processScieloArticleJs(){
    return src(target_src['js']['scielo-article'])
    .pipe(concat(output['js']['scielo-article']))
    .pipe(sourceMaps.init())
    .pipe(stripDebug())
    .pipe(uglify())
    .pipe(sourceMaps.write('../maps'))
    .pipe(dest(output['js']['folder']));
}

// Task para gerar o scielo-bundle.js
function processScieloBundleJs(){
    return src(target_src['js']['scielo-bundle'])
    .pipe(concat(output['js']['scielo-bundle']))
    .pipe(sourceMaps.init())
    //.pipe(stripDebug())
    .pipe(uglify())
    .pipe(sourceMaps.write('../maps'))
    .pipe(dest(output['js']['folder']));
}


// Task para gerar o scielo-bundle-print.less
function processScieloBundlePrintLess(){
    return src(target_src['less']['scielo-bundle-print'])
    .pipe(sourceMaps.init({loadMaps: true}))
    .pipe(concat(output['css']['scielo-bundle-print']))
    .pipe(less(output['css']['scielo-bundle-print']))
    .pipe(minifyCSS())
    .pipe(sourceMaps.write('./'))
    .pipe(dest(output['css']['folder']));
}

// Task para gerar o scielo-article-standalone.less
function processScieloArticleStandaloneLess(){
    return src(target_src['less']['scielo-article-standalone'])
    .pipe(sourceMaps.init({loadMaps: true}))
    .pipe(concat(output['css']['scielo-article-standalone']))
    .pipe(less(output['css']['scielo-article-standalone']))
    .pipe(minifyCSS())
    .pipe(sourceMaps.write('./'))
    .pipe(dest(output['css']['folder']));
}

function processScieloBundleLess(){
    return src(target_src['less']['scielo-bundle'])
    .pipe(sourceMaps.init({loadMaps: true}))
    .pipe(concat(output['css']['scielo-bundle']))
    .pipe(
        less().on('error', function(err) {
            gutil.log(err);
            this.emit('end');
        }))
    .pipe(
        cleanCSS()
    )
    .pipe(
        minifyCSS()
    )
    .pipe(sourceMaps.write('./'))
    .pipe(
        dest(output['css']['folder'])
    )
    .pipe(
        connect.reload()
    );
}

function processScieloArticleLess(){
    return src(target_src['less']['scielo-article'])
    .pipe(sourceMaps.init({loadMaps: true}))
    .pipe(
        less().on('error', function(err) {
            gutil.log(err);
            this.emit('end');
        }))
    .pipe(
        cleanCSS()
    )
    .pipe(
        minifyCSS()
    )
    .pipe(sourceMaps.write('./'))
    .pipe(
        dest(output['css']['folder'])
    )
    .pipe(
        connect.reload()
    );
}

function watchProcessScieloBundleLess() {
    return watch(paths['static_less'], processScieloBundleLess);
}

function watchProcessScieloArticleLess() {
    return watch(paths['static_less'], processScieloArticleLess);
}




/*
Criando Bundle sass
*/
function processScieloBundleSass(){
    return src(target_src['sass']['scielo-bundle'])
    .pipe(sourceMaps.init())
    .pipe(concat(output['css']['scielo-bundle']))
    .pipe(
        sass({ 
            //outputStyle: 'nested',
            includePaths: ['./node_modules/bootstrap/']
        })
    )
    .pipe(include())
    .pipe(cleanCSS())
    .pipe(sourceMaps.write('./'))
    .pipe(dest(output['css']['folder']));
}

/*
Criando Bootstrap Sass
*/
function processBootstrapSass(){
    return src(target_src['sass']['bootstrap'])
    .pipe(sourceMaps.init())
    .pipe(
        sass({ 
            //outputStyle: 'nested',
            includePaths: ['./node_modules/bootstrap/']
        })
    )
    .pipe(include())
    .pipe(cleanCSS())
    .pipe(sourceMaps.write('./'))
    .pipe(dest(output['css']['folder']));
}

/*
Criando Article Sass
*/ 
function processScieloArticleSass(){
    return src(target_src['sass']['scielo-article'])
    .pipe(sourceMaps.init({loadMaps: true}))
    .pipe(
        sass().on('error', function(err) {
            gutil.log(err);
            this.emit('end');
        }))
    .pipe(
        cleanCSS()
    )
    .pipe(
        minifyCSS()
    )
    .pipe(sourceMaps.write('./'))
    .pipe(
        dest(output['css']['folder'])
    )
    .pipe(
        connect.reload()
    );
}


/*
Copiando imagens do design system
*/
function processDesignSystemImg(){
    return src(target_src['img']['logos'])
    .pipe(dest(output['img']['folder']));
}

/*
Copiando bundle bootstrap para dentro do projeto
*/
function processBootstrapBundle(){
    return src('node_modules/bootstrap/dist/js/bootstrap.bundle.js')
    .pipe(dest(output['js']['folder']));
}

exports.watch = series(
    processScieloBundleLess,
    processScieloArticleLess,
   
    parallel(
        watchProcessScieloBundleLess,
        watchProcessScieloArticleLess
    )
)

exports.default = series(
    processScieloBundleLess,
    processScieloArticleLess,
    processScieloArticleStandaloneLess,
    processScieloBundlePrintLess,
    processScieloBundleJs,
    processScieloArticleJs,
    processScieloArticleStandaloneJs
);


/*
Tasks para copiar e gerar arquivos baseados no 
Design System direto do node_modules.
Arquivos Sass
*/
exports.bundleSass = processScieloBundleSass;
exports.bootstrapSass = processBootstrapSass;
exports.processImages = processDesignSystemImg; 
exports.articleSass = processScieloArticleSass;
exports.bootstrapBundleJs = processBootstrapBundle;
exports.scieloBundleJs = processScieloBundleJs;
exports.scieloArticleJs = processScieloArticleJs;

