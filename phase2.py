
import numpy as np
import matplotlib as mp
import os
import dearpygui as dp


class Point:
    # implement

class Request:
    # implement

class Driver:
    # implement

class DispatchPolicy:
    def assign(self,
            drivers: list[Driver],
            requests: list[Request],
            time: int
        ) -> list[tuple[Driver, Request]]:
    """Return proposed (driver, request) pairs for this tick."""
    raise NotImplementedError

class Offer:
    # implement

class DriverBehaviour:
    def decide(self,
                driver: Driver,
                offer: Offer,
                time: int
            ) -> bool:
        """Return True if the driver accepts the offer, False otherwise."""
        raise NotImplementedError

class MutationRule:
    def maybe_mutate(self, driver: Driver, time: int) -> None:
        """Possibly change the driver's behaviour based on performance."""
        raise NotImplementedError

class RequestGenerator:
    def maybe_generate(self, time: int) -> list[Request]:
        """
        Called once per tick. Draws, according to a user's defined rule, and returns N new Request
        objects whose creation_time is 'time' and whose pickup/dropoff points
        are valid positions in the map.
        """
        
class DeliverySimulation:
    def tick(self) -> None:
        """Advance the simulation by one time step."""
        # 1. Generate new requests.
        # 2. Update waiting times and mark expired requests.
        # 3. Compute proposed assignments via dispatch_policy.
        # 4. Convert proposals to offers, ask driver behaviours to accept/reject.
        # 5. Resolve conflicts and finalise assignments.
        # 6. Move drivers and handle pickup/dropoff events.
        # 7. Apply mutation_rule to each driver.
        # 8. Increment time.
    def get_snapshot(self) -> dict:
        """
        Return a dictionary containing:
        - list of driver positions and headings,
        - list of pickup positions (for WAITING/ASSIGNED requests),
        - list of dropoff positions (for PICKED requests),
        - statistics (served, expired, average waiting time).
        Used by the GUI adapter.
        """





    


