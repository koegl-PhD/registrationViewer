from enum import Enum


class Titles(Enum):
    NONE = ""

    USER_ICONS = "STEUERUNGSANLEITUNG"
    STUDY_DESCRIPTION = "STUDIENBESCHREIBUNG"

    WARNING = "Warnung"

    WARNING_POINT_EXISTS = "Punkt {insert} existiert"

    STUDY_INSTRUCTIONS = "STEUERUNGSANLEITUNG"

    STUDY_PAUSED = "STUDIE PAUSIERT"

    STUDY_FINISHED = "STUDIE BEENDET"

    LOADING_DATA = "DATEN WERDEN GELADEN"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)


class Buttons(Enum):
    NONE = ""

    CENTER_ON_USER_POINT = "Zentriere auf deinen Punkt"
    CENTER_ON_GROUND_TRUTH_POINT = "Zentriere auf den Referenzpunkt"
    CENTER_ON_GROUND_TRUTH_LYMPHNODE = "Zentriere auf den Referenzlymphknoten"

    ADD_POINT_BUTTON = "Punkt hinzufügen"
    NEXT_TASK_BUTTON = "Nächste Aufgabe"
    NEXT_PATIENT_BUTTON = "Nächster Patient"
    TRAINING_NEXT_PATIENT_BUTTON = "Nächster Test-Patient"
    TRAINING_NEXT_TASK_BUTTON = "Nächste Testaufgabe"

    DROPDOWN_UNCHANGED = "Größe unverändert"
    DROPDOWN_INCREASED = "Größe vergrößert"
    DROPDOWN_DECREASED = "Größe verkleinert"
    DROPDOWN_RECURRENCE_PRESENT = "Rezidiv vorhanden"

    TURN_TRANSFORMATION_ON = "Transformation aktivieren"
    TURN_TRANSFORMATION_OFF = "Transformation deaktivieren"
    TURN_MANUAL_TRANSFORMATION_ON = "Manuelles verlinken aktivieren"
    TURN_MANUAL_TRANSFORMATION_OFF = "Manuelles verlinken deaktivieren"
    TRANFORMATION_NOT_AVAILABLE = "Transformation nicht verfügbar"

    START_STUDY = "Studie starten"

    FINISH_STUDY = "Studie beenden"

    PROCCED_TO_STUDY = "Zur Studie fortfahren"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value


class Contents(Enum):

    NONE = ""
    STUDY_BEGINS = "HAUPTSTUDIE FÄNGT AN"
    STUDY_DESCRIPTION = f"""
Im Rahmen dieser Studie werden Sie mehrere Annotierungsaufgaben bearbeiten, die alle demselben Muster folgen.
Sie sehen zwei Reihen von CT-Scans, wobei jedes Paar immer vom selben Patienten stammt.
Die obere Reihe zeigt den aktuellsten Scan, den wir „Fixed“ nennen; die untere Reihe zeigt einen älteren Scan, den wir „Moving“ nennen.


Bei einigen Aufgaben sind die beiden Bilder miteinander registriert. Sie können diese Registrierung mit der Taste „t“ oder über den Button "{Buttons.TURN_TRANSFORMATION_ON}" ein- und ausschalten. Dadurch wird Ihre Mausbewegung zwischen den beiden Scans gekoppelt, das heißt: Die Position Ihrer Maus in einem Scan wird an der entsprechenden Stelle im anderen Scan angezeigt.


Achten Sie darauf, die Registrierung zu deaktivieren, wenn Sie von einer Ansicht zur nächsten wechseln.
In jeder Aufgabe müssen Sie einen Punkt in der oberen Reihe (dem neueren Scan) setzen, der einer Struktur im unteren Scan entspricht.


Sie können auf den grünen Info-Button klicken, um die Steuerung anzuzeigen, und auf den orangefarbenen Pause-Button klicken, um die Studie zu pausieren.


Links werden Ihnen vier Buttons angezeigt: zwei zum Zentrieren auf Punkte (einer für den Referenzpunkt und einer für den von Ihnen gesetzten Punkt). Außerdem gibt es einen Button zum Hinzufügen eines Punktes (nach dem Setzen kann dieser an die gewünschte Stelle gezogen werden) sowie einen Button zum Fortfahren mit der nächsten Aufgabe, der aktiviert wird, sobald Sie einen Punkt gesetzt haben.  


Bei Aufgaben zu Lymphknoten erscheint zusätzlich ein Dropdown-Menü, in dem Sie angeben müssen, ob sich der Lymphknoten in der Größe verändert hat.  


Schließlich gibt es bei registrierten Fällen einen Button namens "{Buttons.TURN_TRANSFORMATION_ON}", mit dem die Registrierung aktiviert wird.
        """

    TRAINING_STUDY_DESCRIPTION = f"""
Vor Beginn der eigentlichen Studie werden Ihnen drei Testaufgaben gezeigt. Diese dienen dazu, sich mit der Oberfläche und den Aufgaben vertraut zu machen.

In der ersten Aufgabe wird dasselbe Bild zweimal angezeigt – die Registrierung ist daher perfekt.

In der zweiten Aufgabe wird ebenfalls dasselbe Bild angezeigt, jedoch wurde das untere Bild um 14° rotiert – die Registrierung ist immer noch perfekt, aber die Schnitte stimmen nicht mehr überein.

In der dritten Aufgabe werden zwei Bilder aus unterschiedlichen Sitzungen desselben Patienten gezeigt – es liegt also eine echte Deformation vor, und die Registrierung ist nicht perfekt.

In allen Aufgaben können Sie die Registrierung mit der Taste „t“ oder über den Button "{Buttons.TURN_TRANSFORMATION_ON}" ein- und ausschalten.
Dadurch wird Ihre Mausbewegung zwischen den beiden Scans gekoppelt, das heißt: Die Position Ihrer Maus in einem Scan wird an der entsprechenden Stelle im anderen Scan angezeigt.
    """

    WARNING_REMOVE_RECURRENCE_POINT = "Möchten Sie den Punkt entfernen, den Sie bereits für das Rezidiv gesetzt habt?"

    QUESTION_OVERWRITE_POINT = "Wollen Sie den Punkt überschreiben?"

    OK_TO_RESMUE = "Klicken Sie auf OK, um fortzufahren"

    STUDY_FINISHED = "Danke {insert}, Sie haben die Studie abgeschlossen!"

    CURRENT_TASK = "Aktuelle Aufgabe"
    TRAINING_CURRENT_TASK = "Aktuelle Testaufgabe"

    CURRENT_PATIENT = "Aktueller Patient"
    TRAINING_CURRENT_PATIENT = "Aktueller Test-Patient"

    LOADING_DATA = "Daten werden geladen..."

    CURRENT_PATIENT_COUNTER = "Patient {current}/{total}"
    CURRENT_PATIENT_COUNTER_TRAINING = "Test-Patient {current}/{total}"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)


class ToolTips(Enum):

    NONE = ""

    ADD_POINT_FIRST = "Bitte fügen Sie zuerst einen Punkt hinzu"

    def __str__(self):
        return self.value

    def __repr__(self):
        return self.value

    def format(self, *args, **kwargs):
        return self.value.format(*args, **kwargs)
