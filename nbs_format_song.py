import pynbs
import os
from constants import *

def get_valid_input(valid_inputs: list, msg: str) -> str:
  valid = False

  while not valid:
    user_input = input(msg)

    if user_input in valid_inputs:
      valid = True
    else:
      print(f'"{user_input}" is not a valid input.')
  
  return user_input


def remove_custom_notes(chord: list) -> list:
  new_chord = []

  for note in chord:
    if note.instrument <= 15:
      new_chord.append(note)
    
  return new_chord


def fix_illegal_notes(chord: list) -> list:
  new_chord = []

  for note in chord:
    if note.key < INSTRUMENT_RANGE[0]:
      while note.key < INSTRUMENT_RANGE[0]:
        note.key += 12
    
    elif note.key > INSTRUMENT_RANGE[1]:
      while note.key > INSTRUMENT_RANGE[1]:
        note.key -= 12
    
    new_chord.append(note)

  return new_chord


def remove_helper(chord: list, chord_max_size: int, type: str) -> list:
  if len(chord) <= chord_max_size:
    return chord

  first_note = chord[0]

  for note in chord:
    if type == 'high':
      if note.key > first_note.key:
        first_note = note

    elif type == 'low':
      if note.key < first_note.key:
        first_note = note
  
  chord.remove(first_note)

  return remove_helper(chord, chord_max_size, type)


def remove_notes(chord: list, chord_max_size: int, type: str) -> list:
  lower_octave_notes = []
  upper_octave_notes = []

  for note in chord:
    if note.key < INSTRUMENT_RANGE[0] + 12:
      lower_octave_notes.append(note)
    else:
      upper_octave_notes.append(note)

  lower_octave_notes = remove_helper(lower_octave_notes, chord_max_size, type)
  upper_octave_notes = remove_helper(upper_octave_notes, chord_max_size, type)

  return lower_octave_notes + upper_octave_notes


def remove_chord_violations(chord: list) -> list:
  chord_list = {}
  new_chord = []
  preserved_order_chord = []

  for note in chord:
    if note.instrument in chord_list:
      chord_list[note.instrument].append(note)
    else:
      chord_list[note.instrument] = [note]

  for instrument, single_chord in chord_list.items():
    type = 'high'

    if KEEP_NOTES_BY_INSTRUMENT[INSTRUMENTS[instrument]] == 'h':
      type = 'low'
    
    new_chord.append(remove_notes(single_chord, CHORD_MAX_SIZES[INSTRUMENTS[instrument]], type))
  
  # need to preserve the original note order because sometimes saving has issues when notes are reordered

  for note in chord:
    if note in new_chord:
      preserved_order_chord.append(note)
  
  return [preserved_order_chord, len(preserved_order_chord) < len(chord)]


def main() -> None:
  compress_song = False
  max_chord_violation = False

  while True:
    song_file = input('Please enter the file name of your song (include the .nbs): ')

    if os.path.exists(song_file) == False:
      print('File does not exist. Please try again.')

    else:
      try:
        song = pynbs.read(song_file)
        song_name = song_file[:song_file.find('.nbs')]
        break

      except Exception as error:
        print(f'error: {error}')

  # give user option to compress song
  if song.header.song_length > MAX_SONG_LENGTH:
    print(f'Your song\'s length is {song.header.song_length}, and the max length of a song is {MAX_SONG_LENGTH}.')
  
  print('You might want to compress your song if it is too slow or too long.')
  print('Compressing your song would remove every other tick and make it half as long. This may or may not make your song sound much worse.')

  if get_valid_input(['y', 'n'], 'Would you like to compress your song? (y/n): ') == 'y':
    compress_song = True

  # warn user if there are notes out of range
  for note in song.notes:
    if note.key < INSTRUMENT_RANGE[0] or note.key > INSTRUMENT_RANGE[1]:
      print('Your song contains notes that are outside the normal range. They will be transposed to be playable.')
      input('Press Enter to Continue')
      break
  
  # warn user if there are custom instruments
  if len(song.instruments) > 0:
    print('Your song contains custom instruments. All notes using custom instruments will be removed.')
    input('Press Enter to Continue')
  
  newSong = pynbs.new_file()
  newSong.header, newSong.layers, newSong.header.tempo = song.header, song.layers, 5

  # iterate through the whole song by chords
  for tick, chord in song:
    newTick = tick

    if compress_song == True:
      newTick = tick // 2
    
    if newTick > MAX_SONG_LENGTH:
      print('Notice: Your song was too long, so some had to be cut off the end.')
      break
  
    if (tick % 2 != 0 and compress_song == False) or (tick %2 == 0):
      chord = remove_custom_notes(chord)
      chord = fix_illegal_notes(chord)
      [chord, max_chord_violation] = remove_chord_violations(chord)
      
      for note in chord:
        note.tick, note.panning, note.pitch = newTick, 0, 0
        
        newSong.notes.append(note)
  
  if max_chord_violation == True:
    print('Notice: Your song contained chords that were larger than allowed. Some notes were removed from these chords.')

  # save the new song
  new_file_name = f'{song_name}-(Formatted).nbs'

  newSong.save(new_file_name)
  print('Your formatted song was saved under "', new_file_name, '"')


if __name__ == '__main__':
  main()