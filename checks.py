'''
STATE:
- currentPlayer, whose turn is
- players, the players hands
    list of Player() objects: {name: , hand: [], }
    hand is list of card() objects: {'id': ,'value': , 'color': }
- tableCards, the cards on table: {'red':[], 'yellow':[], 'green':[], 'blue':[], 'white':[]}
    each color is list of card() objects: {id, value, color}
- discardPile, list of card() objects: {id, value, color}
- usedNoteTokens, number of used tokens [0,8]
- usedStormTokens, number of storm tokens gained [0,3]
'''

'''
playerHand: list of card() objects: {id, value, color}
if card is unkown, id=0, value=0, color=None
'''

from calendar import c
from configparser import MAX_INTERPOLATION_DEPTH
from email.policy import default
from re import I
import numpy as np
import random
import game

def checkPlayedOne(state,playerHand): # check if there is a known 1 card that has never been played
    for c in playerHand:
        if c.value==1:
            if len([i for i in state.tableCards if len(state.tableCards[i])>0])==0:
                    return True
            if c.color==None:
                continue
            if len(state.tableCards[c.color])==0:
                return True
    return False

def checkPlayableCard(state,playerHand): # check if there is a known n+1 card in hand w.r.t. the same color n card on table
    for c in playerHand:
        if c.value==0:
            continue
        if c.color==None:
            continue
        if max([i.value for i in state.tableCards[c.color]],default=0) == (c.value-1):
            return True
    return False

def checkFoldableCard(state,playerHand,player): # check if there is a foldable card

    notInDiscardPile = []

    for c in playerHand:
        
        if c.value==0:
            continue
        if c.color==None:
            continue

        if c.value==1:
            checkOnes = [i for i in state.discardPile if i.value==1 and i.color==c.color]
            if len(checkOnes)==2:
                continue

        chk = True
        for d in state.discardPile:
            if c.value==d.value and c.color==d.color:
                chk = False
                break
        if chk:
            notInDiscardPile.append(c)

    if len(notInDiscardPile)==0:
        return False

    for c in notInDiscardPile:
        # dupCheck is a list to check if c has duplicate in hand
        dupCheck = [i for i in notInDiscardPile if i.value==c.value and i.color==c.color]
        if len(dupCheck)>=2:
            return True

        # check if another player has the same card
        for p in state.players:
            if p.name == player:
                continue
            for d in p.hand:    # each card in player p hand
                if d.value==c.value and d.color==c.color:
                    return True

        # check if card has been already played
        if max([i.value for i in state.tableCards[c.color]],default=0)>=c.value:
            return True

    return False

def checkPlayerHasPlayable(state): # check if any player has a playable card
    for p in state.players:
        if checkPlayableCard(state,p.hand):
            return True
    return False

def checkPlayerHasFoldable(state): # check if any player has a foldable card
    for p in state.players:
        if checkFoldableCard(state,p.hand,p.name):
            return True
    return False

def checkRemainingHints(state): # check remaining hint tokens
    if state.usedNoteTokens==0:
        return True,True
    elif state.usedNoteTokens<4:
        return True,False
    elif state.usedNoteTokens<7:
        return False,True
    else:
        return False,False

def checkStormTokens(state): # check how many errors
    if state.usedStormTokens<2:
        return False
    else:
        return True

def getQrow(state,playerHand): # gives an integer corresponding to the T-table row
    checks = [ checkPlayedOne(state,playerHand), checkPlayableCard(state,playerHand), 
               checkFoldableCard(state,playerHand,state.currentPlayer), checkPlayerHasPlayable(state),
               checkPlayerHasFoldable(state), checkStormTokens(state) ] + [i for i in checkRemainingHints(state)]
    return sum([checks[i]*(2**i) for i in range(8)])

def chooseCardToPlay(state,playerHand): # return card index to play
    score = [0,0,0,0,0]
    for c in range(len(playerHand)):
        if playerHand[c].value!=0:
            for color in state.tableCards:
                if max([i.value for i in state.tableCards[color]],default=0) == (playerHand[c].value-1):
                    score[c] += 1       # +1 if the card is +1 than other numbers on the table
                    if color==playerHand[c].color:
                        score[c] += 5   # +5 if the card is the immediately next card for the same color on the table
        if playerHand[c].color!=None:
            if len(state.tableCards[playerHand[c].color])==0:
                score[c] += 1   # +1 if the color isn't on the table
        for p in state.players:
            if p.name == state.currentPlayer:
                continue
            for d in p.hand: # each card in player p hand
                if d.value==playerHand[c].value+1 and d.color==playerHand[c].color:
                    score[c] += 1   # +1 if other players can continue the color in their hand
        if playerHand[c].value==1:
            score[c] += 1   # +1 if the card is one

    best = max(score)
    npscore = np.array(score)
    playable = np.where(npscore==best)[0].tolist()
    ind = random.randint(0,len(playable)-1)
    return playable[ind]

def chooseCardToHint(state,playerHand,hint_memory):     # choose the card to hint according to the hint memory of the other players and the hand of the user
    scores = {}
    color_hints = {}
    value_hints = {}
    for p in state.players:
        if p.name==state.currentPlayer:
            continue
        numbs = {i:0 for i in list(set([c.value for c in p.hand])) }
        cols = {i:0 for i in list(set([c.color for c in p.hand])) } # takes any owned color and transforms in {color: 0}
        
        color_hints[p.name] = [h['color'] for h in hint_memory[p.name] if list(h.keys())[0]=='color']
        value_hints[p.name] = [h['value'] for h in hint_memory[p.name] if list(h.keys())[0]=='value']

        temp_numbs = {}
        for i in numbs:
            if i not in value_hints[p.name]:
                temp_numbs[i] = 0
        
        temp_cols = {}
        for i in cols:
            if i not in color_hints[p.name]:
                temp_cols[i] = 0

        numbs = temp_numbs
        cols = temp_cols

        scores.update({p.name: {'numbers': numbs, 'colors': cols}})
    
    for p in state.players:
        if p==state.currentPlayer:
            continue
        for c in p.hand:
            if max([i.value for i in state.tableCards[c.color]],default=0) == (c.value-1):
                if c.value not in value_hints[p.name]:
                    scores[p.name]['numbers'][c.value] += 20    # +20 if the value could be played
                if c.color not in color_hints[p.name]:
                    scores[p.name]['colors'][c.color] += 20     # +20 if the color could be played
            for d in playerHand:
                if d.value==0 or d.color==None:
                    continue
                if c.color==d.color and (c.value==d.value-1 or c.value==d.value+1):
                    if c.value not in value_hints[p.name]:
                        scores[p.name]['numbers'][c.value] += 1     # +1 if the value is -1 or +1 of another card in the player hand, same colors
                    if c.color not in color_hints[p.name]:
                        scores[p.name]['colors'][c.color] += 1      # +1 if the value is -1 or +1 of another card in the player hand, same colors
                if c.color==d.color and c.value==d.value:
                    if c.value not in value_hints[p.name]:
                        scores[p.name]['numbers'][c.value] += 5     # +5 if another player has the same card (value and color)
                    if c.color not in color_hints[p.name]:
                        scores[p.name]['colors'][c.color] += 5      # +5 if another player has the same card (value and color)
            for q in state.players:
                if q.name==p.name:
                    continue
                for d in q.hand:
                    if d.value==0 or d.color==None:
                        continue
                    if c.color==d.color and (c.value==d.value-1 or c.value==d.value+1):
                        if c.value not in value_hints[p.name]:
                            scores[p.name]['numbers'][c.value] += 1     # if the card is value-1 or value+1 w.r.t other card of another player
                        if c.color not in color_hints[p.name]:
                            scores[p.name]['colors'][c.color] += 1      # if the card is value-1 or value+1 w.r.t other card of another player
                    if c.color==d.color and c.value==d.value:
                        if c.value not in value_hints[p.name]:
                            scores[p.name]['numbers'][c.value] += 5     # if the card is the same of another player's card (colors and values)
                        if c.color not in color_hints[p.name]:
                            scores[p.name]['colors'][c.color] += 5      # if the card is the same of another player's card (colors and values)
            if c.value not in value_hints[p.name]:
                dist = c.value - max([i.value for i in state.tableCards[c.color]],default=0)
                if dist>0:
                    if c.value not in value_hints[p.name]:
                        scores[p.name]['numbers'][c.value] += dist      # +dist w.r.t to the max card of the same color on the table
                    if c.color not in color_hints[p.name]:
                        scores[p.name]['colors'][c.color] += dist       # +dist w.r.t to the max card of the same color on the table
            if c.value==1: 
                if c.value not in value_hints[p.name]:
                    scores[p.name]['numbers'][c.value] += 1             # +1 if he card is one
            if len(state.tableCards[c.color])>0:
                if c.color not in color_hints[p.name]:
                    scores[p.name]['colors'][c.color] += 1              # +1 if the color was played before
            dupCheck = [i for i in p.hand if i.value==c.value and i.color==c.color]
            if len(dupCheck)>=2 or max([i.value for i in state.tableCards[c.color]],default=0) >= c.value or \
                                len([i for i in state.discardPile if i.color==c.color and i.value==c.value])>0:
                if c.value not in value_hints[p.name]:
                    scores[p.name]['numbers'][c.value] += 15    # +15 if the player has a duplicate or the card was already descarded
                if c.color not in color_hints[p.name]:
                    scores[p.name]['colors'][c.color] += 15     # +15 if the player has a duplicate or the card was already descarded
            if c.value == 5:
                if c.value not in value_hints[p.name]:
                    scores[p.name]['numbers'][c.value] += 5     # +5 if the card is a 5
            if c.value not in value_hints[p.name]:
                scores[p.name]['numbers'][c.value] += 5-c.value # +5-value to evaluate better the low cards

            search_value_hint = [h for h in hint_memory[p.name] if 'value' in h and h['value'] == c.value ]
            search_color_hint = [h for h in hint_memory[p.name] if 'color' in h and h['color'] == c.color ]

            if len(search_value_hint) > 0 and len(search_color_hint) > 0:
                continue

            if len(search_value_hint) > 0:
                scores[p.name]['colors'][c.color] += 10     # +10 if there is already an hint on the value
            elif len(search_color_hint) > 0:
                scores[p.name]['numbers'][c.value] += 10    # +10 if there is already an hint on the color

    max_n = {'player': None, 'value': 0, 'points': 0}
    max_c = {'player': None, 'color': None, 'points': 0}

    for s in scores:
        key_list=list(scores[s]['numbers'].keys())      # all numbers
        val_list=list(scores[s]['numbers'].values())    # all points
        hintable = np.where(np.array(val_list)==max(val_list, default=0))[0].tolist()
        if len(hintable)>0:
            ind = hintable[random.randint(0,len(hintable)-1)]
            if val_list[ind] > max_n['points']:     # if better then last found
                max_n['player'] = s
                max_n['points'] = val_list[ind]     # associated points
                max_n['value'] = key_list[ind]      # extracted number

        key_list=list(scores[s]['colors'].keys())   # all colors
        val_list=list(scores[s]['colors'].values()) # all points
        hintable = np.where(np.array(val_list)==max(val_list, default=0))[0].tolist()
        if len(hintable)>0 :
            ind = hintable[random.randint(0,len(hintable)-1)]
            if val_list[ind] > max_c['points']:     # if better then last found
                max_c['player'] = s
                max_c['points'] = val_list[ind]     # associated points
                max_c['color'] = key_list[ind]      # extracted color

    if max_n['player'] == None and max_c['player'] == None:
        return None

    if max_n['points']>max_c['points']:
        return max_n
    elif max_n['points']<max_c['points']:
        return max_c
    else:
        h1 = list(filter(lambda p: p.name == max_n['player'], state.players))[0].hand
        h2 = list(filter(lambda p: p.name == max_c['player'], state.players))[0].hand
        if len([i for i in h1 if i.value == max_n['value']]) > \
           len([i for i in h2 if i.color== max_c['color']]):
            return max_n
        elif len([i for i in h1 if i.value == max_n['value']]) < \
             len([i for i in h2 if i.color == max_c['color']]):
            return max_c
        elif random.randint(0,1):
            return max_n
    return max_c

def chooseCardToDiscard(state, playerHand):
    score = [0,0,0,0,0]
    for c in range(len(playerHand)):
        if playerHand[c].value!=0 and playerHand[c].color!=None:
            dupCheck = [i for i in playerHand if i.value==playerHand[c].value and i.color==playerHand[c].color]
            if (len(dupCheck) >= 2) or max([i.value for i in state.tableCards[playerHand[c].color]], default=0) >= playerHand[c].value:
                score[c] += 10      # +10 if the card was already played of there is a duplicate in the hand (same color and value)
            if (len([i for i in state.discardPile if i.color==playerHand[c].color and i.value==playerHand[c].value]) >0 and playerHand[c].value!=1):
                score[c] -= 10      # -10 if the card is already in the discardPile (same color)
            if (len([i for i in state.discardPile if i.color==playerHand[c].color and i.value==playerHand[c].value]) >1 and playerHand[c].value==1):
                score[c] -= 10      # -10 if the card is one and there are already 2 ones in the discard pile (same color)
            for p in state.players:
                chk = 0
                if (p.name == state.currentPlayer):
                    continue
                for d in p.hand:
                    if (d.value == playerHand[c].value+1 and d.color == playerHand[c].color): 
                        score[c] -= 1   # -1 if the card is value+1 w.r.t. other values on the table
                        chk += 1
                    if (d.value == playerHand[c].value and d.color == playerHand[c].color):
                        score[c] += 1   # +1 if the card is the same of another player (color and value)
                        chk += 1
                if (chk > 1):           # if both conditions above met, break the entire cycle
                    break
        # check if number n-1 with the same color on the table
        if (playerHand[c].color == None):
            for color in state.tableCards:
                if (max([i.value for i in state.tableCards[color]], default=0) == (playerHand[c].value-1)):
                    score[c] -= 1   # -1 if the value of the cards on the table is value-1 w.r.t the card c
        elif (max([i.value for i in state.tableCards[playerHand[c].color]], default=0) == (playerHand[c].value-1)):
            score[c] -= 5           # -5 if on the table there is the card value-1 with the same color
        if playerHand[c].value == 1:
            score[c] -= 1           # -1 if the value is one
        if playerHand[c].color!=None:
            if len(state.tableCards[playerHand[c].color])==0:
                score[c] -= 1       # -1 if the color wasn't already been played
        if playerHand[c].value==5:
            score[c] -= 10          # -10 if the value is 5
        if playerHand[c].color==None and playerHand[c].value==0:
            score[c] -= 5           # -5 if the card in unknown

    best = max(score)
    npscore = np.array(score)
    playable = np.where(npscore==best)[0].tolist()
    ind = random.randint(0,len(playable)-1)
    return playable[ind]

def computeDiscardReward(state,known_card,playerHand):
    reward = 0

    if known_card.color and known_card.value:               # if we already know the card
        if len(state.tableCards[known_card.color]) == 0:    # if the color wasn't been already played
            last = game.Card(0, 0, known_card.color)        # if the value is unknown
        else:
            last = state.tableCards[known_card.color][-1]   # bigger value played of the same color
        if last.value >= known_card.value:                  # the card is useless
            reward += 5
        elif last.value == known_card.value-1:              # the card must be played
            reward -= 5
        else:                                               # the card could be useful
            reward -= 2
    
        discarded_cards = [i for i in state.discardPile if i.color == known_card.color and i.value == known_card.value]
        if known_card.value == 1 and len(discarded_cards) == 2: # if the value is one and there are already 2 one of the same color in the discard pile
            reward -= 10
        elif len(discarded_cards)==1 and known_card.value != 1: # if the value is 2, 3 or 4 and there is already one of them in the discard pile
            reward -= 10

    if known_card.value == 5:       # if the card is 5
        reward -= 10
    if known_card.color == None:    # if the color in unknown
        reward -= 10
    if known_card.value == 0:       # if the value in unknown
        reward -= 10

    # used tokens: (1 2 3 4 5 6 7 8 -> -2 -1 0 1 2 3 4 5)
    reward += state.usedNoteTokens-3 # more tokens have been used more useful is the discard

    complete = [i for i in playerHand if i.color and i.value] # evaluate only the playable cards in the hand
    add_reward = 0
    for i in complete:
        if len(state.tableCards[i.color]) == 0:
            last = game.Card(0,0,i.color)
        else:
            last = state.tableCards[i.color][-1]
        if last.value == i.value-1:         # if there is a playable card in the hand
            add_reward = -10
            break
    if not add_reward:                      # if there aren't playable cards in the hand
        reward += 3
    else:
        reward += add_reward
    
    return reward

def computeHintReward(state,hint,playerHand):
    reward = 0
    complete = [i for i in playerHand if i.color and i.value]
    for i in complete:
        if len(state.tableCards[i.color]) == 0:
            last = game.Card(0, 0, i.color)
        else:
            last = state.tableCards[i.color][-1]
        if last.value == i.value-1:
            reward -= 10    # -10 if there are playable cards in the hand
            break
    if not reward:
        reward += 1
    for c in playerHand:
        if c.value and c.color:
            dupCheck = [i for i in playerHand if i.value==c.value and i.color==c.color]
            if len(state.tableCards[c.color]) == 0:
                last = game.Card(0,0,c.color)
            else:
                last = state.tableCards[c.color][-1]
            if len(dupCheck)>=2 or last.value >= c.value:
                reward -= 2     # -2 if the card is duplicate or already played
                break
    reward -= state.usedNoteTokens
    hintedPlayerHand = list(filter(lambda p: p.name == hint['player'], state.players))[0].hand
    if hint['type'] == 'value':
        target_cards = [i for i in hintedPlayerHand if i.value == hint['value']]
    else:
        target_cards = [i for i in hintedPlayerHand if i.color == hint['value']]
    max_add_reward = 0
    for c in target_cards:
        if len(state.tableCards[c.color]) == 0:
            last = game.Card(0,0,c.color)
        else:
            last = state.tableCards[c.color][-1]
        if c.value-1 == last.value:
            max_add_reward = 3      # 3 if the hintable card could be played
            break
        if c.value > last.value:
            max_add_reward = 1      # 1 if the hintable card could be useful in the future
    reward += max_add_reward
    for c in target_cards:
        if len(state.tableCards[c.color]) == 0:
            last = game.Card(0,0,c.color)
        else:
            last = state.tableCards[c.color][-1]
        dupCheck = [i for i in hintedPlayerHand if i.value==c.value and i.color==c.color]
        if c.value <= last.value or len(dupCheck)>=2:
            reward += 1             # +1 if the hintable card has a duplicate or it was already been played
            break
    if hint['value'] == 5:
        reward += 5                 # +5 if the hintable card is a 5
    
    return reward

