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
    COUPLE_VIEWS = "Manuelles verlinken definieren"
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
Im Rahmen dieser Studie bearbeiten Sie mehrere Annotierungsaufgaben, die alle demselben Muster folgen. Sie sehen zwei Reihen von CT-Scans, wobei jedes Paar vom selben Patienten stammt:
Die obere Reihe zeigt den aktuellsten Scan („Fixed“), die untere Reihe einen älteren Scan („Moving“).

Alle Patient:innen haben eine Tumorresektion im Kopf-Hals-Bereich durchlaufen. Nach der Operation kamen sie regelmäßig zur weiteren CT-Bildgebung zurück. 
Die in dieser Studie gezeigten Aufnahmen zeigen zwei follow-up Bilder, wobei das letzte auf ein Rezidiv untersucht werden muss.

In einigen Aufgaben sind die beiden Bilder miteinander registriert. Die Qualität dieser Registrierungen reicht von schlecht über akzeptabel bis hin zu sehr gut – insbesondere bei Fällen mit starken Deformationen kann die Qualität deutlich variieren. Für Fälle, in denen keine Registrierung verfügbar ist, können Sie die Schichten manuell verlinken, ähnlich wie es in SECTRA möglich ist.

Sie können die Registrierung oder das Verlinken mit der Taste „t“ oder dem Button "{Buttons.TURN_TRANSFORMATION_ON.value}/{Buttons.TURN_MANUAL_TRANSFORMATION_ON.value}" ein- und ausschalten. Ist die Registrierung oder das Verlinken aktiviert, wird Ihre Mausbewegung zwischen den beiden Scans gekoppelt – die Position Ihrer Maus im einen Scan wird also an entsprechender Stelle im anderen Scan angezeigt.
Wir empfehlen Ihnen, eine Hand auf der Taste „t“ zu lassen und mit der anderen Hand die Maus zu bedienen. So können fSie die Registrierung oder das Verlinken schnell ein- und ausschalten, während Sie gleichzeitig die Bilder und Bedienelemente steuern.

Bitte achten Sie darauf, die Registrierung zu deaktivieren, bevor Sie zur einer anderen Ansicht wechseln (Axial, Sagittal, Coronal).

In jeder Aufgabe sollen Sie einen Punkt im oberen Scan (dem aktuelleren Bild) setzen, der einer Struktur im unteren Scan entspricht.
Links stehen Ihnen dafür vier Buttons zur Verfügung:
- Zwei Buttons zum Zentrieren auf Punkte (ein Button für den Referenzpunkt, einer für den von Ihnen gesetzten Punkt),
- ein Button zum Hinzufügen eines neuen Punktes (dieser kann nach dem Setzen verschoben werden),
- sowie ein Button zum Fortfahren mit der nächsten Aufgabe (wird aktiviert, sobald ein Punkt gesetzt wurde).

Zusätzlich können Sie über den grünen Info-Button eine Übersicht der Steuerung aufrufen oder mit dem orangefarbenen Pause-Button die Studie pausieren.
        """

    TRAINING_STUDY_DESCRIPTION = f"""
Bevor die eigentliche Studie beginnt, werden Ihnen Testaufgaben gezeigt. Diese dienen dazu, sich mit der Benutzeroberfläche und dem Ablauf der Aufgaben vertraut zu machen.

In der ersten Testaufgabe wird dasselbe Bild zweimal angezeigt – die Registrierung ist daher perfekt.

In der zweiten Testaufgabe wird ebenfalls dasselbe Bild angezeigt, jedoch wurde das untere Bild um 10° rotiert. Die Registrierung ist weiterhin perfekt, aber die Schichten stimmen nicht mehr exakt überein.

In der dritten Testaufgabe sehen Sie zwei Bilder aus unterschiedlichen CT-Sitzungen desselben Patienten. Es liegt also eine echte Deformation vor, und die Registrierung ist nicht perfekt.

Anschließend werden drei vollständige Testfälle gezeigt

In allen Testaufgaben können Sie die Registrierung oder das Verlinken mit der Taste „t“ oder über den Button "{Buttons.TURN_TRANSFORMATION_ON.value}/{Buttons.TURN_MANUAL_TRANSFORMATION_ON.value}" ein- und ausschalten.
Ist die Registrierung oder das Verlinken aktiviert, wird Ihre Mausbewegung zwischen den beiden Bildern gekoppelt – das heißt: Die Position Ihrer Maus im einen Bild wird an entsprechender Stelle im anderen Bild angezeigt.
Um zu nächsten Aufgabe zu kommen müssen Sie einen Punkt setzen.
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

    REGISTRATION_AVAILABLE = "Registrierung ist verfügbar"
    REGISTRATION_NOT_AVAILABLE = "Registrierung ist nicht verfügbar. Sie können die Bilder manuell verlinken"

    CURRENT_PATIENT_COUNTER = "Patient {current}/{total}\n{registration}."
    CURRENT_PATIENT_COUNTER_TRAINING = "Test-Patient {current}/{total}\n{registration}"

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


"""
Registrierung ist verfügbar
"""
