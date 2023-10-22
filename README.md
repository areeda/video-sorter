# System for categorizing video files

This is a work in process.  We are using it to help our pastime of making 
amateur videos of urban wildlife.


## Our use case
We have multiple Blink cameras around the property and a 
4K trail camera. Fortunately the most interesting videos we
collect contain wild life visiting the property. We enjoy 
making amateur videos of interesting species and antics.

The problem is that we record hundreds of 30 sec videos per day,
most of which are wind rustling plants or animals moving fast enough
that they are out of the frame before the recording starts.

This project is an attempt to facilitate preprocessing and sorting the image files into different
directories.

The directories we use to sort incoming files are based on what we expect. For example
when we look at the blink cameras we separate them by animal after we all out people:
- bird
- cat
- coyote
- possum
- racoon
- rat
- skunk
- squirrel
- other
- furtherReview
- trash

## The workflow
The `vsorter` program leverages any modern browser to present the movies with the option to display 

### preprocessing
If the input movie recordings are in AVI format the `mkmp4` program will convert the video 
and adjust the volume.

MP4 movies can be bassed through the same program for automatic gain control

## Programs

### vsorter - command line preprocessor
The `vsorter` program leverages any modern browser to present the movies with the option to display 
at up to 5x speed or as slow as 0.25x. When the `SUBMIT` button is pressed the indiviual movies
are moved to the apropriate directories.

### vmover - flask app to respond to the web page decisions
The actual moving is done in the background by a Python web application running on the "localhost".

### blink-summary - count movies by camera
When we have a lot of movies to sort I like to do it by camera. This program looks at the
downloaded movies in a directory tree and count how many are from each camera.

