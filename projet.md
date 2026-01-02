**Membres du groupe :**
* Thibault Lebreuil
* Thomas Chu

## **Analyse de la réponse opérationnelle du FDNY à New York**

**Sources de données :**
* FDNY Incendies
[https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data](https://data.cityofnewyork.us/Public-Safety/Fire-Incident-Dispatch-Data/8m42-w767/about_data)
* FDNY Secours à personne
[https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data](https://data.cityofnewyork.us/Public-Safety/EMS-Incident-Dispatch-Data/76xm-jjuj/about_data)
* FDNY liste des centres et compagnies
[https://data.cityofnewyork.us/Public-Safety/FDNY-Firehouse-Listing](https://data.cityofnewyork.us/Public-Safety/FDNY-Firehouse-Listing/hc8x-tcnd/about_data)



### **Angles de vues**

- Répartition du volume d’appels par tranche horaire et par quartier.
- Différences de fréquence d’incidents selon le type d’événement et la saison.
- Performance des casernes selon leur zone géographique et leur charge d’activité.
- Durée des interventions en fonction du type d’incident et du borough.
- Pic d’activité selon les jours de la semaine et les catégories d’incident.
- Analyse des zones sensibles en combinant localisation et périodes de forte affluence.

**Dimensions à explorer:**
* Analyse temporelle des interventions (jour, mois, année, heure).
* Analyse géographique par borough, quartier, caserne, coordonnées.
* Analyse par type d’incident (feu, médical, secours).
* Délais d’intervention et durée estimée sur le terrain.
* Comparaison entre casernes et zones couvertes.
* Relations entre volume d’appels, localisation et période.


## **Exemples de tables et dimensions**

### **Fait_Incidents_Feu**

| Champ             | Rôle             | Description                          |
| ----------------- | ---------------- | ------------------------------------ |
| incident_id       | Clé primaire     | Identifiant unique de l’incident feu |
| datetime_incident | Clé temps        | Date et heure de l’incident          |
| borough           | Clé géographique | Borough de l’incident                |
| zipcode           | Clé géographique | Code postal de l’incident            |
| alarm_box_number  | Attribut métier  | Numéro du boîtier d’alarme           |
| alarm_source      | Attribut métier  | Origine du déclenchement de l’alarme |
| alarm_level_max   | Mesure           | Niveau d’alarme maximal atteint      |
| nb_interventions  | Mesure           | Nombre d’interventions feu           |

---

### **Fait_Incidents_EMS**

| Champ             | Rôle            | Description                              |
| ----------------- | --------------- | ---------------------------------------- |
| incident_id       | Clé primaire    | Identifiant unique de l’intervention EMS |
| datetime_incident | Clé temps       | Date et heure de l’incident              |
| initial_call_type | Attribut métier | Type d’appel initial                     |
| final_call_type   | Attribut métier | Type d’appel final                       |
| initial_severity  | Attribut métier | Gravité initiale                         |
| final_severity    | Attribut métier | Gravité finale                           |
| dispatch_time_s   | Mesure          | Temps de dispatch en secondes            |
| travel_time_s     | Mesure          | Temps de trajet en secondes              |
| response_time_s   | Mesure          | Temps total de réponse                   |
| nb_interventions  | Mesure          | Nombre d’interventions EMS               |

---

### **Dimension temps**

| Champ        | Rôle         | Description        |
| ------------ | ------------ | ------------------ |
| date         | Clé primaire | Date complète      |
| jour         | Attribut     | Jour du mois       |
| mois         | Attribut     | Mois               |
| année        | Attribut     | Année              |
| heure        | Attribut     | Heure              |
| jour_semaine | Attribut     | Jour de la semaine |
| saison       | Attribut     | Saison             |

---

### **Dimension Géographie**

| Champ                 | Rôle         | Description                   |
| --------------------- | ------------ | ----------------------------- |
| borough               | Clé primaire | Borough                       |
| zipcode               | Attribut     | Code postal                   |
| police_precinct       | Attribut     | Commissariat de police        |
| community_district    | Attribut     | District communautaire        |
| city_council_district | Attribut     | District du conseil municipal |
| nta                   | Attribut     | Zone de voisinage statistique |

---

### **Dimension caserne**

| Champ         | Rôle             | Description           |
| ------------- | ---------------- | --------------------- |
| facility_name | Clé primaire     | Nom de la caserne     |
| address       | Attribut         | Adresse de la caserne |
| borough       | Clé géographique | Borough               |
| latitude      | Attribut         | Latitude              |
| longitude     | Attribut         | Longitude             |

---

### **Dimension type d'incident**

| Champ        | Rôle         | Description                              |
| ------------ | ------------ | ---------------------------------------- |
| type_initial | Clé primaire | Type d’incident déclaré                  |
| type_final   | Attribut     | Type d’incident après évaluation         |
| categorie    | Attribut     | Catégorie métier (feu, médical, secours) |

---

### **Dimension niveau de gravité**

| Champ         | Rôle         | Description                       |
| ------------- | ------------ | --------------------------------- |
| severity_code | Clé primaire | Code de gravité                   |
| libelle       | Attribut     | Libellé du niveau de gravité      |
| priorite      | Attribut     | Niveau de priorité opérationnelle |



## **Modèle à adopter ?**

Pour l’instant, on hésite entre un **modèle en étoile** et un **modèle en constellation**, car les deux peuvent, en théorie, répondre à nos besoins d’analyse. Le modèle en étoile certainement faisable. Le modèle en constellation nous semble aussi cohérent dans notre cas puisque nous avons plusieurs tables (incendies et urgence (EMS)) partageant des dimensions communes comme le temps et la géographie. Mais sa structure est plus dense à maîtriser, ce qui nous rend un peu plus hésitants à ce stade, en plus de ne pas savoir si ces deux modèles sont effectivement compatible avec notre entrepôt de données.



## Data Structure
### Fire Incident Dispatch Data

| Colonne                           | Signification estimée                                                           |
| --------------------------------- | ------------------------------------------------------------------------------- |
| **STARFIRE_INCIDENT_ID**          | Identifiant unique de l’incident dans le système opérationnel StarFire du FDNY  |
| **INCIDENT_DATETIME**             | Date et heure exactes de l’enregistrement de l’incident                         |
| **ALARM_BOX_BOROUGH**             | Borough où se situe le boîtier d’alarme ayant déclenché l’intervention          |
| **ALARM_BOX_NUMBER**              | Numéro d’identification du boîtier d’alarme                                     |
| **ALARM_BOX_LOCATION**            | Adresse ou description précise de l’emplacement du boîtier d’alarme             |
| **INCIDENT_BOROUGH**              | Borough où l’incident s’est réellement produit                                  |
| **ZIPCODE**                       | Code postal du lieu de l’incident                                               |
| **POLICEPRECINCT**                | Numéro du commissariat de police de rattachement                                |
| **CITYCOUNCILDISTRICT**           | District du conseil municipal correspondant à la zone de l’incident             |
| **COMMUNITYDISTRICT**             | District administratif communautaire de la zone                                 |
| **COMMUNITYSCHOOLDISTRICT**       | District scolaire couvrant la zone de l’incident                                |
| **CONGRESSIONALDISTRICT**         | District électoral fédéral du Congrès                                           |
| **ALARM_SOURCE_DESCRIPTION_TX**   | Description textuelle de la source de l’alarme (appel, détecteur, témoin, etc.) |
| **ALARM_LEVEL_INDEX_DESCRIPTION** | Libellé textuel du niveau d’alarme déclenché                                    |
| **HIGHEST_ALARM_LEVEL**           | Niveau d’alarme maximal atteint pendant l’intervention                          |

---

### EMS Incident Dispatch Data

| Colonne                            | Signification estimée                                                                     |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| **CAD_INCIDENT_ID**                | Identifiant unique de l’incident dans le système de dispatch assisté par ordinateur (CAD) |
| **INCIDENT_DATETIME**              | Date et heure de création de l’incident EMS                                               |
| **INITIAL_CALL_TYPE**              | Type d’appel tel que déclaré lors du premier contact                                      |
| **INITIAL_SEVERITY_LEVEL_CODE**    | Code de gravité attribué lors de l’appel initial                                          |
| **FINAL_CALL_TYPE**                | Type d’appel après réévaluation par les intervenants                                      |
| **FINAL_SEVERITY_LEVEL_CODE**      | Code de gravité final après diagnostic sur site                                           |
| **FIRST_ASSIGNMENT_DATETIME**      | Date et heure de l’affectation de la première unité EMS                                   |
| **VALID_DISPATCH_RSPNS_TIME_INDC** | Indicateur de validité du temps de réponse de la phase de dispatch                        |
| **DISPATCH_RESPONSE_SECONDS_QY**   | Temps en secondes entre la réception de l’appel et l’envoi d’une unité                    |
| **FIRST_ACTIVATION_DATETIME**      | Date et heure de l’activation opérationnelle de la première unité                         |
| **FIRST_ON_SCENE_DATETIME**        | Date et heure d’arrivée de la première unité sur les lieux                                |
| **VALID_INCIDENT_RSPNS_TIME_INDC** | Indicateur de validité du temps de réponse global de l’incident                           |
| **INCIDENT_RESPONSE_SECONDS_QY**   | Temps total en secondes entre l’appel et l’arrivée sur site                               |
| **INCIDENT_TRAVEL_TM_SECONDS_QY**  | Temps de trajet en secondes entre le départ et l’arrivée sur site                         |
| **FIRST_TO_HOSP_DATETIME**         | Date et heure du premier transport du patient vers l’hôpital                              |

---

### FDNY Firehouse Listing

| Colonne               | Signification estimée                                                          |
| --------------------- | ------------------------------------------------------------------------------ |
| **FacilityName**      | Nom officiel de la caserne ou installation FDNY                                |
| **FacilityAddress**   | Adresse postale complète de la caserne                                         |
| **Borough**           | Borough d’implantation de la caserne                                           |
| **Postcode**          | Code postal de la caserne                                                      |
| **Latitude**          | Latitude géographique du bâtiment                                              |
| **Longitude**         | Longitude géographique du bâtiment                                             |
| **Community Board**   | Numéro du Community Board couvrant la caserne                                  |
| **Community Council** | Numéro du district du conseil municipal                                        |
| **Census Tract**      | Identifiant du secteur de recensement statistique                              |
| **BIN**               | Identifiant unique du bâtiment dans la base urbaine de NYC                     |
| **BBL**               | Code Borough-Block-Lot identifiant la parcelle cadastrale                      |
| **NTA**               | Code ou nom de la zone de voisinage statistique (Neighborhood Tabulation Area) |
