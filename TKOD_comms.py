"""
Module:
nog niet sure wat dit gaat worden maar nu praat het met de OData API
van de tweede kamer om stemmingen op te vragen

Created:
14-3-2023 by Duuk Sikkens

Last edited:
20-3-2023 by Duuk Sikkens
"""

import requests
import json
import time

from typing import List, Dict, Union, Type, Tuple
TypeJSON = Union[Dict[str, 'TypeJSON'], List['TypeJSON'], int, str, float, bool, Type[None]] # Dit is puur voor typehints

URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"  # Locatie tweede kamer API

#========================================================================================================================================
# Classes

class Stemming:

    def __init__(self):

        self.fractiegrootten = dict()
        self.stemmingen = dict()
        self.id = str() # het id van het besluit in de tweede kamer API
        self.stemmingssoort = str()
        self.datum = tuple((int(), int(), int()))
        self.zaaknummer = str()
        self.soort = str()
        self.zaaktitel = str()
        self.zaakciteertitel = str()
        self.onderwerp = str()

    def __str__(self):
        
        string = f'{self.onderwerp}\n\nIngediend bij:\n{self.zaaktitel}\n\nAangenomen: {self.IsAangenomen()}\n\nStemmingen:\n'

        if self.stemmingssoort == 'Met handopsteken':
            for fractie in self.stemmingen:
                string += f'{fractie} ({self.fractiegrootten[fractie]}): ' + {1: 'voor', 0: 'niet deelgenomen', -1: 'tegen'}[self.stemmingen[fractie]] + '\n'
            string += '=============================================================================================\n\n'

        elif self.stemmingssoort == 'Hoofdelijk':
            for lid in self.stemmingen:
                string += f'{lid}: ' + {1: 'voor', 0: 'niet deelgenomen', -1: 'tegen'}[self.stemmingen[lid]] + '\n'
            string += '=============================================================================================\n\n'

        return string
    
    def totaalzetels(self):

        """
        Alvast de mogelijkheid om het totaal aantal zetels af te
        laten hangen van de datum voor als de tweede kamer weer groeit

        Returns: int
        """

        return 150
    
    def IsAangenomen(self):

        """
        Bepaalt of een stemming is aangenomen of verworpen

        Returns: bool
        """

        if len(self.stemmingen) == 0:
            return

        if self.stemmingssoort == 'Met handopsteken':

            stemmenvoor = 0
            for fractie in self.stemmingen:
                if self.stemmingen[fractie] == 1:
                    stemmenvoor += self.fractiegrootten[fractie]
            
            return stemmenvoor > self.totaalzetels() // 2

        elif self.stemmingssoort == 'Hoofdelijk':
            
            stemmenvoor = 0
            for lid in self.stemmingen:
                if self.stemmingen[lid] == 1:
                    stemmenvoor += 1
                
            return stemmenvoor > self.totaalzetels() // 2


#========================================================================================================================================
# Functions

def jsprint(js: TypeJSON, ind: int = 3):

    """
    Print een json dictionary op een overzichtelijke manier

    Returns: None
    """
    
    print(json.dumps(js, indent=ind))

def getstemming(besluit: TypeJSON):

    """
    Bepaald hoe de fracties/kamerleden hebben gestemd om tot een gegeven besluit te komen,
    en de zaak waar het besluit toe behoort.

    Returns: Stemming
    """

    besluitid = besluit['Id']
    stemming = Stemming()
    stemming.stemmingssoort = besluit['StemmingsSoort']
    datumlst = besluit['GewijzigdOp'].split('T')[0].split('-')
    stemming.datum = int(datumlst[0]), int(datumlst[1]), int(datumlst[2])

    # Bepaal hoe de fracties/leden hebben gestemd
    stemmingen = requests.get(url = URL + f"/Besluit({besluitid})?$expand= Stemming").json()['Stemming']
    
    if stemming.stemmingssoort == 'Met handopsteken':
        totzetels = 0
        for s in stemmingen:
            if not s['Verwijderd']:
                stemming.stemmingen[s['ActorFractie']] = {'Voor': 1, 'Niet deelgenomen': 0, 'Tegen': -1}[s['Soort']]
                stemming.fractiegrootten[s['ActorFractie']] = s['FractieGrootte']
                totzetels += s['FractieGrootte']
        
        if totzetels != stemming.totaalzetels():
            print('FOUT: verkeerd aantal zetels bij het volgende besluit')
            jsprint(besluit)
            raise ValueError
    
    elif stemming.stemmingssoort == 'Hoofdelijk':
        totzetels = 0
        for s in stemmingen:
            if not s['Verwijderd']:
                stemming.stemmingen[s['ActorNaam']] = {'Voor': 1, 'Niet deelgenomen': 0, 'Tegen': -1}[s['Soort']]
                totzetels += 1

        if totzetels != stemming.totaalzetels():
            print('FOUT: verkeerd aantal zetels bij het volgende besluit')
            jsprint(besluit)
            raise ValueError     

    # Bepaal de zaak waar de stemming over gaat
    zaken = requests.get(url = URL + f"/Besluit({besluitid})?$expand= Zaak").json()['Zaak']
    if len(zaken) != 1:
        print('FOUT: meer dan één of 0 zaken bij het volgende besluit')
        jsprint(besluit)
        raise ValueError
    
    zaak = zaken[0]
    stemming.zaaknummer = zaak['Nummer']
    stemming.soort = zaak['Soort']
    stemming.zaaktitel = zaak['Titel']
    stemming.zaakciteertitel = zaak['Citeertitel']
    stemming.onderwerp = zaak['Onderwerp']

    return stemming

def getstemming_id(besluitid: str):

    """
    Doet hetzelfde als getstemming maar heeft alleen het id nodig

    Returns: Stemming
    """

    besluit = requests.get(url = URL + f'/Besluit({besluitid})')

    return getstemming(besluit)

def getstemmingen_datum(datum: Tuple[int, int, int]):

    """
    Geeft alle stemmingen op een bepaalde dag (year-month-day)
    
    Returns: List[Stemming]
    """

    y, m, d = datum
    besluiten = requests.get(url = URL + "/Besluit?$filter= (StemmingsSoort eq 'Met handopsteken' or StemmingsSoort eq 'Hoofdelijk') and "\
                                       + f"(year(GewijzigdOp) eq {y} and month(GewijzigdOp) eq {m} and day(GewijzigdOp) eq {d})").json()['value']

    return [getstemming(besluit) for besluit in besluiten]


#========================================================================================================================================
# Testen enzo

def test():
    datum = (2023, 3, 14)
    stemmingen = getstemmingen_datum(datum)
    y, m, d = datum
    f = open(f"stemmingen {y}-{m}-{d}.txt", "w")
    for stemming in stemmingen:
        f.write(str(stemming))
    f.close()

if __name__ == '__main__':
    test()
