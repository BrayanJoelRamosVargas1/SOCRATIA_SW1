from app.modules.p1_gestion_identidad_seguridad.models.user import User
from app.modules.p3_gestion_simulacion.exceptions import SimulationNotFoundError
from app.modules.p3_gestion_simulacion.models import Simulation


class SimulationPolicy:
    @staticmethod
    def assert_owner(user: User, simulation: Simulation | None) -> Simulation:
        if simulation is None or simulation.user_id != user.id:
            raise SimulationNotFoundError
        return simulation

    can_read = assert_owner
    can_delete = assert_owner
    can_calibrate = assert_owner
