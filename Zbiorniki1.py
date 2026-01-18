import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QIntValidator



class Rura:
    def __init__(self, punkty, grubosc=12, kolor=Qt.gray):
        self.punkty = [QPointF(float(p[0]), float(p[1])) for p in punkty]
        self.grubosc = grubosc
        self.kolor_rury = kolor
        self.kolor_cieczy = QColor(0, 180, 255)
        self.czy_plynie = False

    def ustaw_przeplyw(self, plynie):
        self.czy_plynie = plynie

    def draw(self, painter):
        if len(self.punkty) < 2:
            return

        path = QPainterPath()
        path.moveTo(self.punkty[0])
        for p in self.punkty[1:]:
            path.lineTo(p)

        pen_rura = QPen(self.kolor_rury, self.grubosc, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        painter.setPen(pen_rura)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        if self.czy_plynie:
            pen_ciecz = QPen(self.kolor_cieczy, self.grubosc - 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen_ciecz)
            painter.drawPath(path)


class Pompa:
    def __init__(self, x, y, size=60, nazwa="Pompa"):
        self.x = x
        self.y = y
        self.size = size
        self.nazwa = nazwa
        self.aktywna = False

    def punkt_wyjscia(self):
        return (self.x + self.size, self.y + self.size / 2)

    def draw(self, painter):
        pen = QPen(Qt.darkGray, 4)
        painter.setPen(pen)
        painter.setBrush(QColor(70, 70, 70))
        painter.drawRect(self.x, self.y, self.size, self.size)

        painter.setPen(Qt.white)
        painter.drawText(self.x - 5, self.y - 10, self.nazwa)

        if self.aktywna:
            painter.setBrush(QColor(0, 180, 255))
            painter.drawEllipse(
                int(self.x + self.size / 2 - 6),
                int(self.y + self.size / 2 - 6),
                12, 12
            )


class Zbiornik:
    def __init__(self, x, y, width=100, height=140, nazwa=""):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.nazwa = nazwa
        self.aktualna_ilosc = 0.0
        self.poziom = 0.0
        self.poziom_zadany = 100.0  # w procentach (0–100)

    def ustaw_poziom_zadany(self, procent):
        self.poziom_zadany = max(0.0, min(100.0, procent))
    
    def dopasuj_do_zadanego(self, krok=0.5):
        if self.aktualna_ilosc < self.poziom_zadany:
            self.aktualna_ilosc = min(
                self.poziom_zadany,
                self.aktualna_ilosc + krok
            )
            self.poziom = self.aktualna_ilosc / 100.0 
            return "nalewanie"
        elif self.aktualna_ilosc > self.poziom_zadany:
            self.aktualna_ilosc = max(
                self.poziom_zadany,
                self.aktualna_ilosc - krok
            )
            self.poziom = self.aktualna_ilosc / 100.0
            return "oproznianie"
        return None


    def punkt_gora_srodek(self):
        return (self.x + self.width / 2, self.y)

    def draw(self, painter):
        if self.poziom > 0:
            h_cieczy = self.height * self.poziom
            y_start = self.y + self.height - h_cieczy
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 120, 255, 200))
            painter.drawRect(int(self.x + 3), int(y_start), int(self.width - 6), int(h_cieczy - 2))

        pen = QPen(Qt.white, 4)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self.x, self.y, self.width, self.height)
        painter.drawText(self.x, self.y - 10, self.nazwa)


class SymulacjaKaskady(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Symulacja wodociągu")
        self.setFixedSize(900, 600)
        self.setStyleSheet("background-color: #222;")

        self.pompa = Pompa(20, 260)

        self.z1 = Zbiornik(120, 250, nazwa="Zbiornik 1")
        self.z2 = Zbiornik(300, 250, nazwa="Zbiornik 2")
        self.z3 = Zbiornik(480, 250, nazwa="Zbiornik 3")
        self.z4 = Zbiornik(660, 250, nazwa="Zbiornik 4")
        self.zbiorniki = [self.z1, self.z2, self.z3, self.z4]

        # Rura: pompa -> zbiornik 1
        p0 = self.pompa.punkt_wyjscia()
        p1 = self.z1.punkt_gora_srodek()
        mid_y = min(p0[1], p1[1]) - 40
        self.rura0 = Rura([p0, (p0[0] + 30, mid_y), (p1[0], mid_y), p1])

        # Rury między zbiornikami
        self.rura1 = self.polacz(self.z1, self.z2)
        self.rura2 = self.polacz(self.z2, self.z3)
        self.rura3 = self.polacz(self.z3, self.z4)

        self.rury = [self.rura0, self.rura1, self.rura2, self.rura3]

        self.timer = QTimer()
        self.timer.timeout.connect(self.logika_przeplywu)

        self.btn = QPushButton("Start / Stop", self)
        self.btn.setGeometry(20, 540, 120, 30)
        self.btn.clicked.connect(self.przelacz)

        self.running = False
        self.flow_speed = 0.8
        self.ui_poziomy = []

        y_start = 20
        for i, zb in enumerate(self.zbiorniki):
            label = QLabel(f"Zbiornik {i+1}:", self)
            label.setStyleSheet("color: white;")
            label.move(20, y_start + i * 30)

            edit = QLineEdit(self)
            edit.setFixedWidth(50)
            edit.move(100, y_start + i * 30)
            edit.setValidator(QIntValidator(0, 100))
            edit.setText(str(int(zb.poziom_zadany)))
            edit.setStyleSheet("color: white; background-color: #333;")


            percent = QLabel("%", self)
            percent.setStyleSheet("color: white;")
            percent.move(155, y_start + i * 30)

            # reakcja na zmianę
            edit.editingFinished.connect(
                lambda z=zb, e=edit: self.ustaw_poziom_z_ui(z, e)
            )

            self.ui_poziomy.append(edit)

    def ustaw_poziom_z_ui(self, zbiornik, edit):
        try:
            wartosc = float(edit.text())
        except ValueError:
            return

        wartosc = max(0.0, min(100.0, wartosc))
        zbiornik.ustaw_poziom_zadany(wartosc)

    def polacz(self, z1, z2):
        p_start = z1.punkt_gora_srodek()
        p_koniec = z2.punkt_gora_srodek()
        mid_y = min(p_start[1], p_koniec[1]) - 40
        return Rura([p_start, (p_start[0], mid_y), (p_koniec[0], mid_y), p_koniec])

    def przelacz(self):
        if self.running:
            self.timer.stop()
            self.pompa.aktywna = False #Wyłączenie pompy
            for r in self.rury:
                r.ustaw_przeplyw(False) #Przepływ STOP
        else:
            self.timer.start(20)
            
        self.running = not self.running
        self.update()

    def logika_przeplywu(self):
        pompa_plynie = False
        
        for i, zb in enumerate(self.zbiorniki):
            akcja = zb.dopasuj_do_zadanego(self.flow_speed)
            
            if i < len(self.rury):
                self.rury[i].ustaw_przeplyw(akcja == "nalewanie")
                
            if akcja == "nalewanie":
                pompa_plynie = True
                
        self.pompa.aktywna = pompa_plynie
        self.update()

        

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        for r in self.rury:
            r.draw(p)
        self.pompa.draw(p)
        for z in self.zbiorniki:
            z.draw(p)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    okno = SymulacjaKaskady()
    okno.show()
    sys.exit(app.exec_())
