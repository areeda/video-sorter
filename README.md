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

The directories we use to sort incoming files are:
- Good: probably will include part of it
- Poor: contains something interesting enough to not delete it
- Other: Something interesting but on the topic
- Trash: To be deleted

## The workflow
If the input movie recordings are

### preprocessing


## Programs

### vsorter - command line preprocessor

### movie2gif - utility to create animated thumbnails

### vmover - flask app to respond to the web page decisions