# Neusician

In my world, ideal free online services should be, at least in one respect, like traditional unix-tools: They should do only one thing, and they should do it well. They should work with a smallest footprint of dependencies possible. Everything else be in the scope of other tools that are better suited for the individual user.

Neusician is not that ideal. It does two separate things. Both parts interact in the endeavour of teaching the interested audience the Sompyler/YAML language in an interactive way, and each part can be simply left aside.

## Pseudo-random melody generator

* Seeded by a preferably short english or german phrase of user's choice and
* accompanied with a preset *probabilistic fingerprint* – overwritable by the user, to be saved at any rate –
  * that encodes the used tone scale, i.e. the tone names and the possible intervals, and
  * describes very concisely the Markov chains for their interrelations to make up a specific musical style,

the service outputs a melody in the following plain text notation: `C4 1, C4 1, G4 1, G4 1, A4 1, A4 1, G4 2, ...`

This is the beginning of "Twinkle, Twinkle, Little Star", you should have recognized it. The probability that the service yields a melody known like this is close to zero when given an orthographically correct english or german phrase, at will spiced with numbers and/or any interpunctuation. Most of the time, the melody yielded will be quite a challenge to work upon by beginning composers.

The comma-separated parts of the notation each imply a leading zero and space, meaning there are no pulse-beats (i.e. ticks of unspecified duration) of rest between them and the note before. The integer after the note name denotes the ticks of duration that the note lasts. It is as simple as that.


### What to do with the melody notated like this?

Keyboard or piano players can then go try it on their instrument and test and play with the melody. Here composition starts: Harmony and disharmony, musical form, dynamics and tempo, instrumentation and stuff, all is up to the composer to make something worth listening to, just like a jeweler makes a diamond from a piece of dirty stone (well, the dirty stone we know still needs to be extremely compressed carbon).

Just try to work upon the given inspiration, apply as little essential variations to it as possible, and ask your friends, parents or piano teacher: "Is this a random bunch of tones or is it music?" – the reply will improve from time to time. Go to a library for books (or, well, an online shop), or surf the internet for resources on composition of music, to accelerate the learning process.

Given the same seed phrase and the same probabilistic fingerprint every time, the algorithm will yield the same melody, too. This is determinism, this is the pseudo- in the pseudo-randomness.

### Why not start from a purely random bunch of tones which would be much simpler to implement?

By applying pseudo-randomness and saving the algorithmic derivation from the seed phrase(s) to the characteristic motives (riffs) of your work, accidental plagiarism is rather unlikely to hurt you bad, perhaps less likely than with an inspiration apparently coming out of your head, showing original creativity that is prone to foggily subconsciously remembering a melody once known and still not yours.

But, in case you are confronted with accidental plagiarism after using this algorithm notwithstanding, you can try tell at least something different from "But I did not copy!" for your defense. But let noone claim that would change the judgement or the result of the Content-ID algorithm, right?


## Online Sompyler score and instruments editor

(To do)


# Copyright

(C) 2020 Florian 'flowdy' Heß

See LICENSE containing the General public license, version 3.

Sompyler is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Sompyler is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sompyler. If not, see <http://www.gnu.org/licenses/>.