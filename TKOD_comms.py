"""
Module:
nog niet sure wat dit gaat worden maar nu praat het met de OData API
van de tweede kamer om stemmingen op te vragen

Created:
14-3-2023 by Duuk Sikkens

Last edited:
17-3-2023 by Duuk Sikkens
"""

import requests
import json

from typing import List, Dict, Union, Type, Tuple
TypeJSON = Union[Dict[str, 'TypeJSON'], List['TypeJSON'], int, str, float, bool, Type[None]] # Dit is puur voor typehints

URL = "https://gegevensmagazijn.tweedekamer.nl/OData/v4/2.0"  # Locatie tweede kamer API

#========================================================================================================================================
# Classes

class Stemming:

    def __init__(self):

        self.fractiegrootten = dict()
        self.stemmingen = dict()
        self.id = str() # het id van de zaak in de tweede kamer API
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

def getstemmingen(datum: Tuple[int, int, int]):

    """
    Geeft alle stemmingen van partijen op een bepaalde dag (year-month-day)
    
    Returns: List[Stemming]
    """

    y, m, d = datum
    besluiten = requests.get(url = URL + "/Besluit?$filter= (StemmingsSoort eq 'Met handopsteken' or StemmingsSoort eq 'Hoofdelijk') and "\
                                       + f"(year(GewijzigdOp) eq {y} and month(GewijzigdOp) eq {m} and day(GewijzigdOp) eq {d})").json()['value']

    stemmingenlst = []
    for besluit in besluiten:
        if not besluit['Verwijderd']:

            # Bepaal hoe de partijen hebben gestemd
            besluitid = besluit['Id']
            stemming = Stemming()
            stemming.stemmingssoort = besluit['StemmingsSoort']
            stemming.datum = datum

            stemmingen = requests.get(url = URL + f'/Besluit({besluitid})?$expand= Stemming').json()['Stemming']
            
            if stemming.stemmingssoort == 'Met handopsteken':
                for s in stemmingen:
                    if not s['Verwijderd']:
                        stemming.stemmingen[s['ActorFractie']] = {'Voor': 1, 'Niet deelgenomen': 0, 'Tegen': -1}[s['Soort']]
                        stemming.fractiegrootten[s['ActorFractie']] = s['FractieGrootte']
            
            elif stemming.stemmingssoort == 'Hoofdelijk':
                for s in stemmingen:
                    if not s['Verwijderd']:
                        stemming.stemmingen[s['ActorNaam']] = {'Voor': 1, 'Niet deelgenomen': 0, 'Tegen': -1}[s['Soort']]

            # Bepaal de zaak waar de stemming over gaat
            zaken = requests.get(url = URL + f"/Besluit({besluitid})?$expand= Zaak").json()['Zaak']
            if len(zaken) != 1:
                raise ValueError
                """
                TODO:
                Code schrijven die ons erop attendeert dat één stemming fsr over meerdere zaken ging
                """
            
            zaak = zaken[0]
            stemming.id = zaak['Id']
            stemming.zaaknummer = zaak['Nummer']
            stemming.soort = zaak['Soort']
            stemming.zaaktitel = zaak['Titel']
            stemming.zaakciteertitel = zaak['Citeertitel']
            stemming.onderwerp = zaak['Onderwerp']

            stemmingenlst.append(stemming)

    return stemmingenlst

def isbijectief(filter: str = ''):
    if filter == '':
        besluiten = requests.get(url = URL + "/Besluit?$filter= StemmingsSoort eq 'Met handopsteken' or StemmingsSoort eq 'Hoofdelijk'").json()['value']
    else:
        besluiten = requests.get(url = URL + f"/Besluit?$filter= (StemmingsSoort eq 'Met handopsteken' or StemmingsSoort eq 'Hoofdelijk') and ({filter})").json()['value']
    
    for besluit in besluiten:
        besluitid = besluit['Id']
        zaken = requests.get(url = URL + f"/Besluit({besluitid})?$expand= Zaak").json()['Zaak']
        if len(zaken) != 1:
            jsprint(besluit)
            jsprint(zaken)
            return

        zaak = zaken[0]
        zaakid = zaak['Id']
        besluitenn = requests.get(url = URL + f"/Zaak({zaakid})?$expand= Besluit($filter = StemmingsSoort eq 'Met handopsteken' or StemmingsSoort eq 'Hoofdelijk')").json()['Besluit']
        if len(besluitenn) != 1:
            besluitids = [besluitt['Id'] for besluitt in besluitenn]
            jsprint(zaak)
            jsprint(besluitenn)
            return (besluitids, zaakid)




#========================================================================================================================================
# Testen enzo

def test():
    datum = (2023, 3, 14)
    stemmingen = getstemmingen(datum)
    y, m, d = datum
    f = open(f"stemmingen {y}-{m}-{d}.txt", "w")
    for stemming in stemmingen:
        f.write(str(stemming))
    f.close()

def test2():
    besluitids, zaakid = isbijectief()
    for besluitid in besluitids:
        stemmingen = requests.get(url = URL + f'/Besluit({besluitid})?$expand= Stemming').json()['Stemming']
        jsprint(besluitid)
        jsprint(stemmingen)

if __name__ == '__main__':
    test2()