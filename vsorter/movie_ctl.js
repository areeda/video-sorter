function movie_start(id, speed)
{
    movie = $jQuery('#id');
    movie.playbackRate = speed;
    movie.play();
}