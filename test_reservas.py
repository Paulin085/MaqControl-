# test_reservas.py — Testes automatizados do módulo de Reserva de Salas
import unittest
from datetime import date, datetime, timedelta
import os
import sys

# Garante que o diretório raiz está no path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from models.reserva import ReservaCreate, SalaOpcoes, StatusReserva, ReservaUpdate
from crud.crud_reservas import validar_reserva, criar_reserva, atualizar_reserva, excluir_reserva, listar_reservas, buscar_reserva

class TestReservaSalas(unittest.TestCase):
    def setUp(self):
        # Limpa/salva arquivo reservas.json temporário para testes
        self.original_data_file = "data/reservas.json"
        self.backup_data_file = "data/reservas_backup_test.json"
        
        if os.path.exists(self.original_data_file):
            if os.path.exists(self.backup_data_file):
                os.remove(self.backup_data_file)
            os.rename(self.original_data_file, self.backup_data_file)
            
        with open(self.original_data_file, "w", encoding="utf-8") as f:
            f.write("[]")

    def tearDown(self):
        # Restaura backup
        if os.path.exists(self.original_data_file):
            os.remove(self.original_data_file)
        if os.path.exists(self.backup_data_file):
            os.rename(self.backup_data_file, self.original_data_file)

    def test_validacao_horarios(self):
        # 1. Início >= Fim deve falhar
        reserva = ReservaCreate(
            sala=SalaOpcoes.REUNIAO,
            titulo="Reunião Teste",
            data=date.today(),
            hora_inicio="15:00",
            hora_fim="14:00"
        )
        ok, msg = validar_reserva(reserva)
        self.assertFalse(ok)
        self.assertIn("menor que", msg)

        # 2. Data passada deve falhar
        reserva_passada = ReservaCreate(
            sala=SalaOpcoes.REUNIAO,
            titulo="Reunião Passada",
            data=date.today() - timedelta(days=1),
            hora_inicio="10:00",
            hora_fim="11:00"
        )
        ok, msg = validar_reserva(reserva_passada)
        self.assertFalse(ok)
        self.assertIn("passadas", msg)

    def test_conflito_horarios(self):
        # Cria primeira reserva das 10:00 às 11:30
        reserva1 = ReservaCreate(
            sala=SalaOpcoes.REUNIAO,
            titulo="Reserva Principal",
            data=date.today() + timedelta(days=1), # data futura para evitar bloqueio de hoje
            hora_inicio="10:00",
            hora_fim="11:30"
        )
        ok, msg = validar_reserva(reserva1)
        self.assertTrue(ok, msg)
        
        criar_reserva(reserva1, "test-user-1")

        # Tenta criar uma segunda reserva com sobreposição das 11:00 às 12:00 na mesma sala
        reserva_conflito = ReservaCreate(
            sala=SalaOpcoes.REUNIAO,
            titulo="Reserva Conflitante",
            data=date.today() + timedelta(days=1),
            hora_inicio="11:00",
            hora_fim="12:00"
        )
        ok, msg = validar_reserva(reserva_conflito)
        self.assertFalse(ok)
        self.assertIn("já está reservada", msg)

        # Tenta criar uma reserva em horário diferente na mesma sala (deve passar)
        reserva_ok_mesma_sala = ReservaCreate(
            sala=SalaOpcoes.REUNIAO,
            titulo="Reserva OK Mesma Sala",
            data=date.today() + timedelta(days=1),
            hora_inicio="11:30",
            hora_fim="12:30"
        )
        ok, msg = validar_reserva(reserva_ok_mesma_sala)
        self.assertTrue(ok, msg)

        # Tenta criar uma reserva no mesmo horário em sala diferente (deve passar)
        reserva_ok_outra_sala = ReservaCreate(
            sala=SalaOpcoes.TREINAMENTO,
            titulo="Reserva Outra Sala",
            data=date.today() + timedelta(days=1),
            hora_inicio="10:00",
            hora_fim="11:30"
        )
        ok, msg = validar_reserva(reserva_ok_outra_sala)
        self.assertTrue(ok, msg)

    def test_crud_completo(self):
        reserva = ReservaCreate(
            sala=SalaOpcoes.TREINAMENTO,
            titulo="Treinamento Integradores",
            data=date.today() + timedelta(days=2),
            hora_inicio="14:00",
            hora_fim="17:00"
        )
        # Create
        created = criar_reserva(reserva, "user-teste")
        self.assertIsNotNone(created.id)
        self.assertEqual(created.titulo, "Treinamento Integradores")

        # Read (listar)
        lista = listar_reservas(sala=SalaOpcoes.TREINAMENTO.value)
        self.assertEqual(len(lista), 1)
        self.assertEqual(lista[0].id, created.id)

        # Read (buscar por ID)
        found = buscar_reserva(created.id)
        self.assertIsNotNone(found)
        self.assertEqual(found.titulo, "Treinamento Integradores")

        # Update
        update_payload = ReservaUpdate(titulo="Treinamento Modificado", status=StatusReserva.CONCLUIDA)
        updated = atualizar_reserva(created.id, update_payload)
        self.assertEqual(updated.titulo, "Treinamento Modificado")
        self.assertEqual(updated.status, StatusReserva.CONCLUIDA)

        # Delete
        success = excluir_reserva(created.id)
        self.assertTrue(success)
        self.assertIsNone(buscar_reserva(created.id))

if __name__ == "__main__":
    unittest.main()
