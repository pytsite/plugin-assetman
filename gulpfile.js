const fs = require('fs');
const yargs = require('yargs');
const gulp = require('gulp');
const ignore = require('gulp-ignore');
const minify = yargs.argv['minify'] === 'yes';

function minifyJS(s) {
    const jsmin = require('gulp-minify');

    return s.pipe(jsmin({
        ext: {
            min: '.js'
        },
        noSource: true
    }));
}

function minifyCSS(s) {
    const cssmin = require('gulp-cssmin');

    return s.pipe(cssmin());
}

function copy(stream) {
    return stream;
}

function copyStatic(stream) {
    const filter = ignore.include(/\.(png|jpg|jpeg|gif|svg|ttf|woff|woff2|eot|otf|map|min\.js|min\.css)$/);

    return stream.pipe(filter)
}

function js(stream, args) {
    stream = stream.pipe(ignore.include(/\.js$/));
    stream = stream.pipe(ignore.exclude(/\.(min|pack)\.js$/));

    if (args.babelify) {
        const babel = require('gulp-babel');

        stream = stream.pipe(babel({
            presets: ['@babel/env']
        }));
    }

    // Minify
    if (minify)
        stream = minifyJS(stream);

    return stream;
}


function css(stream) {
    stream = stream.pipe(ignore.include(/\.css$/));
    stream = stream.pipe(ignore.exclude(/\.(min|pack)\.css$/));

    // Minify
    if (minify)
        stream = minifyCSS(stream);

    return stream;
}

function less(stream) {
    const gulpLess = require('gulp-less');

    stream = stream.pipe(ignore.include(/\.less/)).pipe(gulpLess());

    // Minify
    if (minify)
        stream = minifyCSS(stream);

    return stream;
}

function scss(stream) {
    const gulpSass = require('gulp-sass');

    stream = stream.pipe(ignore.include(/\.scss/)).pipe(gulpSass());

    // Minify
    if (minify)
        stream = minifyCSS(stream);

    return stream;
}


gulp.task('default', function () {
    const tasksFile = yargs.argv.tasksFile;

    if (!tasksFile)
        throw 'Tasks file path is not specified';

    fs.readFile(yargs.argv.tasksFile, 'utf8', function (err, data) {
        if (err) {
            return console.log(err);
        }

        const tasks = JSON.parse(data);
        for (let i = 0; i < tasks.length; i++) {
            const task = tasks[i];
            let stream = gulp.src(task.source);

            switch (task.name) {
                case 'copy':
                    stream = copy(stream, task.args);
                    break;

                case 'copy_static':
                    stream = copyStatic(stream, task.args);
                    break;

                case 'css':
                    stream = css(stream, task.args);
                    break;

                case 'less':
                    stream = less(stream, task.args);
                    break;

                case 'scss':
                    stream = scss(stream, task.args);
                    break;

                case 'js':
                    stream = js(stream, task.args);
                    break;

                default:
                    throw 'Unknown task: ' + task.name;
            }

            stream.pipe(gulp.dest(task.destination));
        }
    });
});
