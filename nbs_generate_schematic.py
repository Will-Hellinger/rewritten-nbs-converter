import pynbs
import os
import sys
import numpy
import mcschematic
from constants import *


def verify_format(song: pynbs.Song) -> None:
  valid = True

  print('Verifying your song...')

  # check song length
  print('Checking song length...')
  if song.header.song_length > MAX_SONG_LENGTH:
    print('Warning: Your song is too long.')
    valid = False
  
  # check custom instruments
  print('Checking for custom instruments...')
  if len(song.instruments) > 0:
    print('Warning: Your song contains custom instruments.')
    valid = False

  # check range
  print('Checking note ranges...')
  for note in song.notes:
    if note.key < INSTRUMENT_RANGE[0] or note.key > INSTRUMENT_RANGE[1]:
      print('Warning: Your song contains notes that are outside the normal range.')
      valid = False

      break

  # check chord lengths
  print('Checking chord lengths...')
  for tick, chord in song:
    chord_list = {}

    for note in chord:
      if note.instrument in chord_list:
        chord_list[note.instrument].append(note)
      else:
        chord_list[note.instrument] = [note]
    
    for instrument, singleChord in chord_list.items():
      lowerOctaveNotes = []
      upperOctaveNotes = []

      for note in singleChord:
        if note.key < INSTRUMENT_RANGE[0] + 12:
          lowerOctaveNotes.append(note)
        else:
          upperOctaveNotes.append(note)
      
      if len(lowerOctaveNotes) > CHORD_MAX_SIZES[INSTRUMENTS[instrument]] or len(upperOctaveNotes) > CHORD_MAX_SIZES[INSTRUMENTS[instrument]]:
        print('Warning: Your song contains chords that are larger than allowed.')
        valid = False
        break

    if valid == False:
      break

  if valid == False:
    sys.exit('We found some issues with your song. Please make sure to format it using the "nbs_format_song" script.')
  else:
    print('Song verified. Everything looks good!')


def remove_empty_chests(chest_contents: dict) -> dict:
  newchest_contents = {}

  for instrument, contents in chest_contents.items():
    newchest_contents[instrument] = []

    for octaves in contents:
      new_octaves = [[], []]
      empty_lower_octave = True
      empty_higher_octave = True

      for note in octaves[0]:
        if note != -1:
          empty_lower_octave = False
          break

      for note in octaves[1]:
        if note != -1:
          empty_higher_octave = False
          break
      
      if empty_lower_octave == False:
        new_octaves[0] = octaves[0]

      if empty_higher_octave == False:
        new_octaves[1] = octaves[1]
      
      newchest_contents[instrument].append(new_octaves)
  
  return newchest_contents


def new_disc(slot, note: int) -> str:
  if note == -1:
    return '{Count:1b,Slot:' + str(slot) + 'b,id:"minecraft:wooden_shovel"}'
  
  if note >= 12:
    note -= 12
  
  disc = NOTES_TO_DISCS_UNNAMED[note]
  if NAME_DISCS == 1:
    disc = NOTES_TO_DISCS_NAMED[note]

  return '{Count:1b,Slot:' + str(slot) + 'b,id:' + disc + '}'


def create_shulker(current_shulker, contents: str) -> str:
  slot = (current_shulker - 1) % 27
  # remove trailing comma
  contents = contents[:len(contents) - 1]

  return '{Count:1b,Slot:' + str(slot) + 'b,id:"minecraft:shulker_box",tag:{BlockEntityTag:{CustomName:\'{"text":"' + str(current_shulker) + '"}\',Items:[' + contents + '],id:"minecraft:shulker_box"},display:{Name:\'{"text":"' + str(current_shulker) + '"}\'}}}'


def create_chest(type: str, contents: str) -> str:
  # remove trailing comma
  if len(contents) > 0:
    contents = contents[:len(contents) - 1]
  
  return 'minecraft:chest[facing=south,type=' + type + ']{Items:[' + contents + ']}'


def create_sign(instrument: str, current_module, octave: int) -> str:
  octave_message = 'upper octave'

  if octave == 0:
    octave_message = 'lower octave'
  
  return 'minecraft:oak_wall_sign[facing=south,waterlogged=false]{front_text:{color:"black",has_glowing_text:0b,messages:[\'{"text":"' + instrument + ' ' + str(current_module) + '"}\',\'{"text":"' + octave_message + '"}\',\'{"text":""}\',\'{"text":""}\']},is_waxed:0b}'


def main() -> None:
  # get song file from user
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
  
  verify_format(song)

  # fix the length of the song for min fill of last chest
  last_chest_fill = (song.header.song_length + 1) % 27
  song_length_adjusted = song.header.song_length + 1

  if last_chest_fill >= 1 and last_chest_fill < CHEST_MIN_FILL:
    song_length_adjusted += CHEST_MIN_FILL - last_chest_fill

  # initialize data structure
  allchest_contents = {}
  emptyChest = numpy.full(song_length_adjusted, -1)

  for instrument in INSTRUMENTS:
    allchest_contents[instrument] = []
    for i in range(CHORD_MAX_SIZES[instrument]):
      allchest_contents[instrument].append([emptyChest.copy(), emptyChest.copy()])

  # iterate through the whole song by chords
  key_modifier = INSTRUMENT_RANGE[0]
  currentIndices = {}
  
  for tick, chord in song:
    # reset current indices
    for instrument in INSTRUMENTS:
      currentIndices[instrument] = [0, 0]
    
    for note in chord:
      instrument = INSTRUMENTS[note.instrument]
      adjusted_key = note.key - key_modifier

      octave = 1
      if adjusted_key <= 11:
        octave = 0
        
      allchest_contents[instrument][currentIndices[instrument][octave]][octave][tick] = adjusted_key
      currentIndices[instrument][octave] += 1
  
  minimalchest_contents = remove_empty_chests(allchest_contents)

  # turn minimalchest_contents into a schematic
  schem = mcschematic.MCSchematic()
  offset = 0

  print('Generating Schematic...')
  for instrument, contents in minimalchest_contents.items():
    for current_module in range(len(contents)):
      module = contents[i]

      lowerChest1 = ''
      upperChest1 = ''
      lowerChest2 = ''
      upperChest2 = ''
      lowerShulker = ''
      upperShulker = ''
      current_shulker = 1
      lowerOctaveEmpty = len(module[0]) == 0
      upperOctaveEmpty = len(module[1]) == 0
      
      for currentTick in range(song_length_adjusted):
        currentSlot = currentTick % 27

        if lowerOctaveEmpty == 0:
          lowerShulker += new_disc(currentSlot, module[0][currentTick]) + ','
        
        if upperOctaveEmpty == 0:
          upperShulker += new_disc(currentSlot, module[1][currentTick]) + ','

        # if we are on the last slot of a shulker box, or the song has ended
        if (currentTick + 1) % 27 == 0 or currentTick == song_length_adjusted - 1:
          # turn the shulker contents into actual shulker
          if lowerOctaveEmpty == 0:
            lowerShulker = create_shulker(current_shulker, lowerShulker)
          
          if upperOctaveEmpty == 0:
            upperShulker = create_shulker(current_shulker, upperShulker)
          
          # if the current shulker should go in the first chests
          if current_shulker <= 27:
            if lowerOctaveEmpty == 0:
              lowerChest1 += lowerShulker + ','
            
            if upperOctaveEmpty == 0:
              upperChest1 += upperShulker + ','
            
          else:
            if lowerOctaveEmpty == 0:
              lowerChest2 += lowerShulker + ','
            
            if upperOctaveEmpty == 0:
              upperChest2 += upperShulker + ','
          
          # reset the shulkers and increment the current shulker
          lowerShulker = ''
          upperShulker = ''
          current_shulker += 1
      
      if lowerOctaveEmpty == 0:
        lowerChest1 = create_chest('right', lowerChest1)
        lowerChest2 = create_chest('left', lowerChest2)
        schem.setBlock((offset, 0, -1), lowerChest1)
        schem.setBlock((offset + 1, 0, -1), lowerChest2)
        schem.setBlock((offset, 0, 0), create_sign(instrument, current_module, 0))

      else:
        schem.setBlock((offset, 0, -1), "minecraft:air")
        schem.setBlock((offset + 1, 0, -1), "minecraft:air")
        schem.setBlock((offset, 0, 0), "minecraft:air")
      
      if upperOctaveEmpty == 0:
        upperChest1 = create_chest('right', upperChest1)
        upperChest2 = create_chest('left', upperChest2)
        schem.setBlock((offset, 1, -1), upperChest1)
        schem.setBlock((offset + 1, 1, -1), upperChest2)
        schem.setBlock((offset, 1, 0), create_sign(instrument, current_module, 1))

      else:
        schem.setBlock((offset, 1, -1), "minecraft:air")
        schem.setBlock((offset + 1, 1, -1), "minecraft:air")
        schem.setBlock((offset, 1, 0), "minecraft:air")
      
      offset += 2
  
  saveName = song_name.lower().replace('(', '').replace(')', '').replace(' ', '_')
  schem.save('', saveName, mcschematic.Version.JE_1_20)
  print('Your schematic was successfully generated and saved under "' + saveName + '.schem"')


if __name__ == '__main__':
  main()