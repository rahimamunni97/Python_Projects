# main module

# ToDO later:
    # maybe devide into files
    # remember to include docstrings and later also doctests
    # improve durability against wrong use

# ToDo now:
    # I finished the first couple of classes. Next Couple of steps:
    # 1) Implement DriverBehaviour (Bipasha)
    # 2) Implement DisoatchPolicy (Bipasha)(let me (Janek) know when finished)
    # 3) Implement RequestGenerator (Janek)
    # 4) Implement DeliverySimulation (Lubaba) (let Bipasha when finished)
    # 5) Implement MutationRule (Bipasha)


import numpy as np


class Point: # Janek
    """
    Value class representing a position on the map.
    
    Attributes:
        x: float
        y: float
    """
    x: float
    y: float

    def __init__ (self, x: float, y: float) -> None:
        """
        Initializes a point with x and y coordinates.
        """
        self.x = x
        self.y = y
        
    def distance_to(self, other: Point) -> float:
        """
        Returns the Euclidean distance between this point and other.

        Idea:
        x_dist = other.x.__sub__(self.x)
        y_dist = other.y.__sub__(self.y)
        distance = np.sqrt(int.__mul__(x_dist, x_dist).__add__(int.__mul__(y_dist, y_dist)))
        """

        x_dist = self.x - other.x
        y_dist = self.y - other.y
        distance = np.sqrt(x_dist**2 + y_dist**2)

        return distance
        
    def __add__ (self, other: Point):
        """
        normal addition of points in 2D coordinate system
        """
        if not isinstance(other, Point):
            raise TypeError("not a point")
        return Point(self.x + other.x, self.y + other.y)

    def __sub__ (self, other: Point):
        """
        normal substraction of points in 2D coordinate system
        """
        if not isinstance(other, Point):
            raise TypeError("not a point")
        return Point(self.x - other.x, self.y - other.y)
        
    def __iadd__ (self, other: Point):
        """
        addition - for modifying excisting point instead of creating new one (in 2D cooradinate system)
        """
        if not isinstance(other, Point):
            raise TypeError("not a point")
        self.x += other.x
        self.y += other.y
        return self

    def __isub__ (self, other: Point):
        """
        subtraction - for modifying excisting point instead of creating new one (in 2D coordinate system)
        """
        if not isinstance(other, Point):
            raise TypeError("not a point")
        self.x -= other.x
        self.y -= other.y
        return self

    def __mul__ (self, scalar, (float | int)):
        """
        defined both for multiplcations for int and float (!!)
        """
        if not isinstance(scalar (int, float)):
            raise TypeError("not a scalar")
        return Point(self.x * scalar, self.y * scalar)

    def __rmul__ (self, scalar, (float | int)):
        """
        defined both for multiplcations for int and float (!!)
        """
        if not isinstance(scalar (int, float)):
            raise TypeError("not a scalar")
        return  self.__mul__(scalar) #uds

        

class Request: # Janek
    """
    Represents a single food-delivery request with pickup and drop-off locations.

    Attributes:
        – id: int
        – pickup: Point
        – dropoff: Point
        – creation_time: int (simulation tick at which the request appeared)
        – status: str (for example"WAITING","ASSIGNED","PICKED","DELIVERED","EXPIRED")
        – assigned_driver_id: int | None
        – wait_time: int (time spent in the system until pickup/delivery)
    """

    id: int
    pickup: Point
    dropoff: Point
    creation_time: int
    status: str
    assigned_driver_id: int | None
    wait_time: int
    

    def __init__(self, id: int, pickup: Point, dropoff: Point, creation_time: int) -> None:
        """
        Initializes a new request. 
        """
        self.id = id
        self.pickup = pickup
        self.dropoff = dropoff
        self.creation_time = creation_time
        self.status = "WAITING"
        self.assigned_driver_id = None
        self.wait_time = 0

    def is_active(self) -> bool:
        """
        Returns True if the request is still waiting, assigned, or picked (that is, not delivered or
        expired).
        """
        if self.status == "WAITING" or self.status == "ASSIGNED" or self.status == "PICKED":
            return True
        return False

    def mark_assigned(self, driver_id: int) -> None:
        """
        Marks the request as assigned to a driver. 
        """
        if self.status == "WAITING" and self.assigned_driver_id is None:
            self.status = "ASSIGNED"
            self.assigned_driver_id = driver_id

    def mark_picked(self, t: int) -> None:
        """
        Marks the request as picked. 
        """
        if self.status == "ASSIGNED" and self.assigned_driver_id is not None:
            self.status = "PICKED"

    def mark_delivered(self, t: int) -> None:
        """
        Marks the request as delivered.
        """
        if self.status == "PICKED" and self.assigned_driver_id is not None:
            self.status = "DELIVERED"

    def mark_expired(self, t: int, max_wait: int) -> None:
        """
        Marks the request as expired. 
        """
        if (t - self.creation_time) >= max_wait:
            self.status = "EXPIRED"

    def update_wait(self, current_time: int) -> None:
        """
        Updates wait_time according to current_time.
        """
        self.wait_time = current_time - self.creation_time
        

    

class Driver: # Janek
    """
    Represents a driver agent that can move on the map and accept or reject offers

    Attributes:
        – id: int
        – position: Point
        – speed: float (units per tick)
        – status: str (for example"IDLE","TO_PICKUP","TO_DROPOFF")
        – current_request: Request | None
        – behaviour: DriverBehaviour
        – history: list (to store recent completed trips, earnings, and similar statistics)
    """

    id: int
    position: Point
    speed: float
    status: str
    current_request: Request | None
    behaviour: DriverBehaviour
    history: list

    def __init__(self, id: int, position: Point, speed: float):
        """
        Initializes a new driver. 
        """
        self.id = id
        self.position = position
        self.speed = speed
        self.status = "IDLE"
        self.current_request = None
        self.behaviour = EarningsMaxBehaviour() # lets say first, everyone wants to make the most money and then they get exhausted --> greedy distance if they went to far or lazy if they earned enough money 
        self.history = []
        
    def assign_request(self, request: Request, current_time: int) -> None:
        """
        If the driver is IDLE, we assign a request and set the status
        to "TO_PICKUP".
        """
        if self.status == "IDLE" and self.current_request is None:
            self.current_request = request
            self.status = "TO_PICKUP"
            request.mark_assigned(self.id) # dont call mark_assigned in dispatcher then
        
    def target_point(self) -> Point | None:
        """
        Returns the next target: the pickup point if status is "TO_PICKUP", or the drop-off point if
        status is "TO_DROPOFF".
        """
        if self.current_request is None:
            return None
        if self.status == "TO_PICKUP":
            return self.current_request.pickup
        if self.status == "TO_DROPOFF":
            return self.current_request.dropoff
        return None

    def step(self, dt: float) -> None:
        """
        Moves the driver towards the current target according to speed and the time step dt.
        """
        target = self.target_point()
        distance_can_move = self.speed * dt
        if target is None:
            return None
        distance = self.position.distance_to(target)

        if distance == 0:
            return None
        if distance_can_move >= distance:
            self.position = target
        if distance_can_move < distance:
            distance_x = target.x - self.position.x
            distance_y = target.y - self.position.y
            factor = distance_can_move / distance
            
            self.position = Point(self.position.x + distance_x * factor,
                                  self.position.y + distance_y * factor)
       
    def complete_pickup(self, time: int) -> None:
        """
        Updates internal state when the pickup is reached.
        """
        if self.current_request is None:
            return None
        if self.status == "TO_PICKUP":
            self.status = "TO_DROPOFF"
            self.current_request.mark_picked(time)

    def complete_dropoff(self, time: int) -> None:
        """
        Updates internal state and history when the drop-off is reached.
        """
        if self.current_request is None:
            return None
        if self.status == "TO_DROPOFF":
            self.current_request.mark_delivered(time)
            self.history.append(("DELIVERED", self.current_request.id, time)) # make sure in correct location that also expired is appended to the list
            self.current_request = None
            self.status = "IDLE"

    

class DispatchPolicy: # Bipasha
    def assign(
            self,
            drivers: list[Driver],
            requests: list[Request],
            time: int
        ) -> list[tuple[Driver, Request]]:
    """Return proposed (driver, request) pairs for this tick."""
    raise NotImplementedError

class Offer: # Janek
    """
    A data object describing a proposal from the dispatcher to a driver.

    Attributes:
        – driver: Driver
        – request: Request
        – estimated_travel_time: float
        – estimated_reward: float (if you choose a reward model)
    """

    driver: Driver
    request: Request
    estimated_travel_time: float
    estimated_reward: float

    def __init__(self, driver: Driver, request: Request):
        """
        Initializes the Offer of requests to drivers.
        For the estimated reward, 0.0 is set as a placeholder. # might change later
        """
        self.driver = driver
        self.request = request
        self.estimated_reward = 0.0

        dist_to_pickup = driver.position.distance_to(request.pickup)
        trip_dist = request.pickup.distance_to(request.dropoff)
        total_dist = dist_to_pickup + trip_dist
        if driver.speed <= 0:
            self.estimated_travel_time = float("inf")
        else:
            self.estimated_travel_time = total_dist / driver.speed


class DriverBehaviour: # Bipasha
    def decide(self,
                driver: Driver,
                offer: Offer,
                time: int
            ) -> bool:
        """Return True if the driver accepts the offer, False otherwise."""
        raise NotImplementedError

class MutationRule: # Bipasha
    def maybe_mutate(self, driver: Driver, time: int) -> None:
        """Possibly change the driver's behaviour based on performance."""
        raise NotImplementedError

class RequestGenerator: # Janek
    """
    The arrival of new requests follows a fixed average rate - modelled as a
    separate object.

    Attributes:
        – rate: float (expected number of new requests per tick),
        – a random number generator,
        – next_id: int (for request identifiers),
        – map boundaries (width and height)

    """

    rate: float
    # random number generator
    next_id: int
    # map boundaries
    
    def maybe_generate(self, time: int) -> list[Request]:
        """
        Called once per tick. Draws, according to a user's defined rule, and returns N new Request
        objects whose creation_time is 'time' and whose pickup/dropoff points
        are valid positions in the map.
        """
        
class DeliverySimulation: # Lubaba
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





    


