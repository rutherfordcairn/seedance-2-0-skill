# Seedance 2.0 input notes

The three catalog IDs share a 4–15 second output range. The regular model has
480p, 720p, 1080p and 4K tiers; Fast and Mini expose 480p and 720p. A request
can contain up to 9 images, 3 videos and 3 audio tracks, with at most 15
reference assets in total. Reference media is named in the prompt as
`@Image N`, `@Video N`, and `@Audio N`. A first/last-frame request uses
`start_image` and `end_image`; an edit request is a separate mode carrying one
source video. Confirm current limits on the model page before a production job.
