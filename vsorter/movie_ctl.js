function movie_start(movie_id, speed_label_id, speed)
{
    movie = $jQuery('#id');
    movie.playbackRate = speed;
    movie.play();
    var speed_label = $jQuery('#speed_label');
    speed_label.innerHTML = speed.toFixed(2);
}