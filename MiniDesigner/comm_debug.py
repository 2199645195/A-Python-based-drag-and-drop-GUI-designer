#!/usr/bin/env python3
"""comm_debug.py — 通信调试面板（串口/TCP）"""
import re, socket, threading, time
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QPlainTextEdit, QLCDNumber, QGroupBox, QSlider, QSpinBox, QDoubleSpinBox)
from PySide6.QtGui import QFont


class CommDebugPanel(QWidget):
    tag_received = Signal(str, str)
    def __init__(self, canvas, parent=None):
        super().__init__(parent)
        self.canvas = canvas
        self.setMinimumWidth(200); self.setMaximumWidth(400)
        l = QVBoxLayout(self); l.setContentsMargins(0,0,0,0); l.setSpacing(4)
        h = QLabel("<b>🔌 通信调试</b>")
        h.setStyleSheet("padding:4px 8px;font-size:12px;background:#f0f0f0;border-bottom:1px solid #ddd;")
        l.addWidget(h)
        pr = QHBoxLayout(); self.cb = QComboBox()
        self.cb.addItems(["TCP Client","Serial (COM)"])
        self.cb.currentIndexChanged.connect(self._on_proto)
        pr.addWidget(QLabel("协议:")); pr.addWidget(self.cb); l.addLayout(pr)
        self.eh = QLineEdit("127.0.0.1"); self.ep = QLineEdit("502")
        self.ec = QLineEdit("COM1"); self.eb = QComboBox()
        self.eb.addItems(["9600","115200","38400","19200","4800"])
        self.rt = QWidget(); t = QFormLayout(self.rt); t.setContentsMargins(0,0,0,0)
        t.addRow("IP:",self.eh); t.addRow("Port:",self.ep)
        self.rs = QWidget(); s = QFormLayout(self.rs); s.setContentsMargins(0,0,0,0)
        s.addRow("端口:",self.ec); s.addRow("波特率:",self.eb)
        p = QWidget(); v = QVBoxLayout(p); v.setContentsMargins(4,2,4,2)
        v.addWidget(self.rt); v.addWidget(self.rs); l.addWidget(p)
        tr = QHBoxLayout(); self.et = QLineEdit(); self.et.setPlaceholderText("目标Tag")
        tr.addWidget(QLabel("→Tag:")); tr.addWidget(self.et); l.addLayout(tr)
        br = QHBoxLayout()
        self.bc = QPushButton("🔗 连接"); self.bc.setStyleSheet("QPushButton{background:#27AE60;color:#fff;border:none;border-radius:4px;padding:4px 12px;font-size:11px;font-weight:bold;}")
        self.bd = QPushButton("❌ 断开"); self.bd.setEnabled(False)
        self.bd.setStyleSheet("QPushButton{background:#E74C3C;color:#fff;border:none;border-radius:4px;padding:4px 12px;font-size:11px;font-weight:bold;}")
        self.bs = QPushButton("📤 发送"); self.bs.setStyleSheet("QPushButton{padding:4px 8px;font-size:11px;}")
        br.addWidget(self.bc); br.addWidget(self.bd); l.addLayout(br)
        sr = QHBoxLayout(); self.es = QLineEdit(); self.es.setPlaceholderText("发送...")
        sr.addWidget(self.es); sr.addWidget(self.bs); l.addLayout(sr)
        self.rv = QPlainTextEdit(); self.rv.setReadOnly(True); self.rv.setMaximumHeight(200)
        self.rv.setStyleSheet("QPlainTextEdit{font-family:Consolas,monospace;font-size:11px;background:#1e1e1e;color:#d4d4d4;border:1px solid #333;border-radius:4px;padding:4px;}")
        l.addWidget(self.rv)
        self.sl = QLabel("⚪ 未连接"); self.sl.setStyleSheet("font-size:11px;color:#888;padding:2px 4px;")
        l.addWidget(self.sl)
        self.bc.clicked.connect(self._con); self.bd.clicked.connect(self._dis)
        self.bs.clicked.connect(self._send); self.es.returnPressed.connect(self._send)
        self._sock = None; self._ser = None; self._conn = False
        self._on_proto(0)

    def _on_proto(self, i): self.rt.setVisible(i==0); self.rs.setVisible(i!=0)
    def _log(self, m):
        self.rv.appendPlainText(f"[{time.strftime('%H:%M:%S')}] {m}")
        self.rv.verticalScrollBar().setValue(self.rv.verticalScrollBar().maximum())
    def _con(self):
        try:
            if self.cb.currentIndex()==0:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(3); self._sock.connect((self.eh.text(),int(self.ep.text())))
                self._sock.settimeout(None); self._log(f"✅ TCP {self.eh.text()}:{self.ep.text()}")
            else:
                import serial
                self._ser = serial.Serial(self.ec.text(),int(self.eb.currentText()),timeout=1)
                self._log(f"✅ 串口 {self.ec.text()}@{self.eb.currentText()}")
            self._conn=True; self.bc.setEnabled(False); self.bd.setEnabled(True)
            self.sl.setText("🟢 已连接"); self.sl.setStyleSheet("font-size:11px;color:#27AE60;padding:2px 4px;font-weight:bold;")
            threading.Thread(target=self._recv_loop,daemon=True).start()
        except ImportError: self._log("❌ 需 pip install pyserial")
        except Exception as e: self._log(f"❌ {e}")
    def _dis(self):
        self._conn=False
        if self._sock: self._sock.close(); self._sock=None
        if self._ser: self._ser.close(); self._ser=None
        self.bc.setEnabled(True); self.bd.setEnabled(False)
        self.sl.setText("⚪ 未连接"); self.sl.setStyleSheet("font-size:11px;color:#888;padding:2px 4px;")
        self._log("🔌 断开")
    def _recv_loop(self):
        while self._conn:
            try:
                d=None
                if self._sock: d=self._sock.recv(1024)
                elif self._ser: d=self._ser.read(self._ser.in_waiting or 1)
                if d:
                    t=d.decode('utf-8',errors='replace').strip()
                    QTimer.singleShot(0,lambda x=t: self._on_data(x))
            except: break
    def _on_data(self,t):
        self._log(f"📥 RX: {t}")
        tag=self.et.text().strip()
        if tag:
            m=re.search(r'[-+]?\d*\.?\d+',t)
            if m:
                self.tag_received.emit(tag,m.group())
                for w in self.canvas._canvas_widgets:
                    if w.property("_tag")==tag:
                        try:
                            v=float(m.group())
                            if isinstance(w,(QLabel,QLineEdit)): w.setText(m.group())
                            elif isinstance(w,(QProgressBar,QSlider)): w.setValue(int(v))
                            elif isinstance(w,QLCDNumber): w.display(v)
                        except: pass
    def _send(self):
        t=self.es.text().strip()
        if not t: return
        try:
            d=t.encode('utf-8')
            if self._sock: self._sock.sendall(d)
            elif self._ser: self._ser.write(d)
            self._log(f"📤 TX: {t}"); self.es.clear()
        except Exception as e: self._log(f"❌ {e}")
    def cleanup(self): self._dis()
