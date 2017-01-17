====================================
API za vremenske podatke v Sloveniji
====================================


Namen
=====

Namen te storitve je ponuditi v nadalnjo rabo podatke o stanju vremena v
Sloveniji. Storitev je s strani Kiberpipe brezplačna, potrebno pa je
spoštovati avtorsko pravico in navesti vire podatkov, ki jih uporabljate.

Format zapisa
=============

Vsi podatki so na voljo v JSON zapisu. Vsak odgovor ima poleg izvirnih
podatkov, še nekaj dodatnih podatkov:

copyright
  string, vsebuje naziv nosilca avtorske pravice nad podatki.

updated
  float, unix timestamp, vsebuje podatek o tem, kdaj so bili podatki
  posodobljeni.

Kjer so izvirni podatki koordinate, so dodane še koordinate v prostorskem
referenčnem sistemu WGS84.

Vsak klic v primeru napake vrne odgovor::

  null

Podatki
=======

Podatki so trenutno na voljo na http://opendata.si. Hostname se lahko v
prihodnje spremeni.

Vreme na določenih koordinatah
------------------------------

URL: `/vreme/report/`_

**GET parametri:**

lat
  float, ki predstavlja zemljepisno širino, npr. 46.051418. Veljavne
  vrednosti so med 45.21 in 47.05.

lon
  float, ki predstavlja zemljepisno dolžino, npr. 14.505971. Veljavne
  vrednosti so med 12.92 in 16.71.

**Struktura vrnjenega rezultata:**

radar
  vsebuje informacije o padavinah

rain_level
  jakost padavin v relativnih enotah iz radarske slike pred majem 2014 - je eno
  izmed 0 (bela), 25 (zelena), 50 (rumena), 75 (oranžna) ali 100 (rdeča)

rain_mmph
  jakost padavin v milimetrih na uro

x, y
  sta koordinati na transformirani sliki in sta načeloma namenjena debugiranju

hailprob
  odsek vsebuje informacije o predvideni toči

hail_level
  je eno izmed 0, 33, 66 ali 100 v naraščujoči verjetnosti toče

forecast
  odsek je modelska napoved vremena ALADIN

clouds
  pokritost neba z oblaki v odstotkih

rain
  dež v milimetrih padavin na triurno obdobje napovedi

offset
  časovni odmik od napovedi v urah.

**Primer zahtevka**

https://opendata.si/vreme/report/?lat=47.05&lon=12.92

**Primer vrnjenega rezultata**::

  {
    "status": "ok",
    "copyright": "ARSO, Agencija RS za okolje",
    "lon": "12.92",
    "forecast": {
        "y": 139,
        "x": 32,
        "updated": 1319277600,
        "data": [
            {
                "forecast_time": "2011-10-22 20:00",
                "clouds": 0,
                "rain": 0,
                "offset": 6
            },
            ...
        ]
    },
    "radar": {
        "y": 156,
        "updated_text": "2011-10-22 19:39",
        "updated": 1319305162,
        "rain_level": 0,
        "rain_mmph": 0,
        "x": 99
    },
    "lat": "47.05",
    "hailprob": {
        "y": 52,
        "updated_text": "2011-10-22 19:48",
        "updated": 1319305695,
        "hail_level": 0,
        "x": 5
    }
  }


Vir podatkov: Agencija RS za okolje, http://www.arso.gov.si/


KML za Google Maps
------------------

Za razvoj sem za preverjanje uporabil Google maps, za katerega je na
voljo `KML s polprosojno sliko vremena po Sloveniji`_.

.. _`KML s polprosojno sliko vremena po Sloveniji`: https://maps.google.com/?q=http://opendata.si/vreme/kml/radar.kml
.. _`/vreme/kml/radar.kml`: http://opendata.si/vreme/kml/radar.kml
.. _`/vreme/report/`: http://opendata.si/vreme/report/
