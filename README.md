Neusician
=========

In my world, ideal free online services should be, at least in one respect, like traditional unix-tools:
They should do only one thing, and they should do it well.
They should work with a smallest footprint of dependencies possible.
Everything else be in the scope of tools better suited for the individual user.

Neusician is not that ideal. It does two separate things.
Both parts interact in the endeavour of teaching the Sompyler/YAML language in an interactive way.
Musicians might be interested, but computer nerds with creative/music affinity.

And each part can be simply left aside.


Pseudo-random melody generator
------------------------------

* Seeded by a preferably short english or german phrase of user's choice and
* accompanied with a preset *probabilistic fingerprint* – overwritable by the user, to be saved at any rate –
  * that encodes the used tone scale, i.e. the tone names and the possible intervals, and
  * describes very concisely the Markov chains for their interrelations to make up a specific musical style,
* finally an optional "intuitive spice" number that encodes *tiny* tweaks to the melody, will be 0 by default
  (does not need to be 0, however, if by a composer who passed you the link of the generator with all
  the used parameters incorporated, to prove his melody is close to what the algorithm yielded),

the service outputs a melody in the following plain text notation: `C4 1, C4 1, G4 1, G4 1, A4 1, A4 1, G4 2, ...`

This is the beginning of "Twinkle, Twinkle, Little Star", you should have recognized it.
The probability that the algorithm yields a melody well-known like this is close to zero.
Especially when given an orthographically correct english or german phrase.
Most of the time, the output melody will be quite a challenge to work with for beginning composers.

The comma-separated parts of the notation each imply a leading zero and space.
That means there are no pulse-beats (i.e. ticks of unspecified duration) of rest between them and the proceeding note.
The integer after the note name denotes the ticks of duration that the note lasts.
It is as simple as that.


### What to do with the melody notated like this?

Keyboard or piano players can then go try it on their instrument and test and play with the melody.
Here composition starts: Harmony and disharmony, musical form, dynamics and tempo, instrumentation and stuff –
all is up to the composer to make something worth listening to, just like a jeweler makes a diamond from a piece of dirty stone.
(Well, the dirty stone we know still needs to be extremely compressed carbon.)

Just try to work upon the given inspiration.
Apply as little essential variations to it as possible.
Ask your friends, parents or piano teacher: "Is this a random bunch of tones or is it music?"
The reply will improve from time to time.
To accelerate the learning process, you may want to go to a library for books
(or, well, an online shop), or surf the internet for resources on composition of music.

Given the same seed phrase and the same probabilistic fingerprint every time, the algorithm will yield the same melody, too.
This is determinism, this is the pseudo- in the pseudo-randomness.


### Why not start from a purely random bunch of tones which would be much simpler to implement?

By applying pseudo-randomness and saving the algorithmic derivation from the seed phrase(s) to the characteristic motives (riffs) of your work, accidental plagiarism is rather unlikely to hurt you bad.
Perhaps less likely than with an inspiration apparently coming out of your head.
Original creativity that is prone to foggily subconsciously remembering a melody once known, but still not yours.

In case you are confronted with accidental plagiarism after using this algorithm notwithstanding, you can try tell at least something different from "But I did not copy!" for your defense.
But let noone claim that would always change the judgement, not to forget the result of the Content-ID algorithm, right?


Online Sompyler score and instruments editor
--------------------------------------------

You do not need to hack the melody into your piano or keyboard for instance, especially if you haven't any.
You can have the notes converted into Sompyler note chain syntax.

For our example children's song, this would be: `C4 8 o.o_o+7.o_o++.o_o--_3`.
For a start, the melody is put as the first measure.
The first measure is automatically enriched with metadata like stress pattern for a 4/4 time and everything that is mandatory.
The instrument is preset to one from a template.

You can add and change every single item in the score and the instrument.
Every item has got an appropriate widget popping up when you click it.

Then you can feed all that YAML text to your local installation of [Sompyler](https://gitlab.com/flowdy/Sompyler).


### Why there is not an online sound synthesis built-in

There will be a binding for Sompyler.

But the provider of a Neusician server instance might not want to give you an account.
An account enables you to render the music to an audio file directly on the instance.
The processing has a heavy footprint in terms of cpu and memory resources.

Even if the provider has set up a few exclusive accounts for friends and themselves, this might turn out hardly bearable for the instance.
When someone uses the online sound synthesis facility, the webserver might process requests slower.

Sompyler has not been developped with strong machine-level efficiency in mind.
And originally, it also has not been developped with online users in mind.
After all, it is Python, even if Numpy and optionally Cython is used for mass math.

Installation
------------

Configure instance/config.py.

In templates/, copy base.tmpl.stub to base.tmpl and customize
it to your website style.


Copyright
---------

(C) 2020 Florian 'flowdy' Heß

See LICENSE containing the General public license, version 3.

Neusician is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Neusician is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Neusician. If not, see <http://www.gnu.org/licenses/>.
