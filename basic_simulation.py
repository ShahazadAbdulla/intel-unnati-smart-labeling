import pybullet as p
import time 
import pybullet_data
import math

# --- PyBullet Setup ---
physicsClient = p.connect(p.GUI)
p.setAdditionalSearchPath(pybullet_data.getDataPath())
p.setGravity(0, 0, -9.81)
planeId = p.loadURDF("plane.urdf")

# --- Shared Product Properties ---
product_half_extents = [0.05, 0.05, 0.05] 

# --- Conveyor & Scene Parameters ---
inspection_x_limit = 0.0 
conveyor_half_extents = [1.5, 0.2, 0.05] 
conveyor_height_above_ground = 0.5
conveyor_end_x = conveyor_half_extents[0] - product_half_extents[0] - 0.05 

# --- Conveyor Belt & Legs (Copied from your code, assumed correct) ---
conveyor_position = [0, 0, conveyor_height_above_ground + conveyor_half_extents[2]]
conveyor_orientation = p.getQuaternionFromEuler([0, 0, 0])
conveyor_visual_shape_id = p.createVisualShape(shapeType=p.GEOM_BOX, halfExtents=conveyor_half_extents, rgbaColor=[.5, .5, .5, 1])
conveyor_collision_shape_id = p.createCollisionShape(shapeType=p.GEOM_BOX, halfExtents=conveyor_half_extents)
conveyor_id = p.createMultiBody(baseMass=0, baseCollisionShapeIndex=conveyor_collision_shape_id, baseVisualShapeIndex=conveyor_visual_shape_id, basePosition=conveyor_position, baseOrientation=conveyor_orientation)
leg_half_extents = [0.05, 0.05, conveyor_height_above_ground / 2.0]
leg_visual_shape_id = p.createVisualShape(shapeType=p.GEOM_BOX, halfExtents=leg_half_extents, rgbaColor=[0.4, 0.4, 0.4, 1])
leg_collision_shape_id = p.createCollisionShape(shapeType=p.GEOM_BOX, halfExtents=leg_half_extents)
leg_x_offset = conveyor_half_extents[0] * 0.8 
leg_z_position = conveyor_height_above_ground / 2.0
p.createMultiBody(baseMass=0, baseCollisionShapeIndex=leg_collision_shape_id, baseVisualShapeIndex=leg_visual_shape_id, basePosition=[-leg_x_offset, 0, leg_z_position], baseOrientation=p.getQuaternionFromEuler([0,0,0]))
p.createMultiBody(baseMass=0, baseCollisionShapeIndex=leg_collision_shape_id, baseVisualShapeIndex=leg_visual_shape_id, basePosition=[leg_x_offset, 0, leg_z_position], baseOrientation=p.getQuaternionFromEuler([0,0,0]))

# --- Product Initialization Values ---
product_mass = 0.2
product_start_y = 0.0 
product_start_z = (conveyor_position[2] + conveyor_half_extents[2]) + product_half_extents[2] + 0.001 
product_start_orientation = p.getQuaternionFromEuler([0, 0, 0])

# --- Multiple Product Setup ---
num_products = 6
product_spacing = 0.25 
products_data = [] 
batch_colors = [ [0.8,0.2,0.2,1], [0.2,0.8,0.2,1], [0.2,0.2,0.8,1], [0.8,0.8,0.2,1] ]
rearmost_product_start_x = -conveyor_half_extents[0] + product_half_extents[0] + 0.05 
for i in range(num_products):
    current_product_start_x = rearmost_product_start_x + i * product_spacing
    prod_start_pos = [current_product_start_x, product_start_y, product_start_z]
    batch_idx = 0
    if i < 1: batch_idx = 3      
    elif i < 2: batch_idx = 2    
    elif i < 4: batch_idx = 1    
    else: batch_idx = 0          
    prod_color = batch_colors[batch_idx]
    vis_id = p.createVisualShape(shapeType=p.GEOM_BOX, halfExtents=product_half_extents, rgbaColor=prod_color)
    col_id = p.createCollisionShape(shapeType=p.GEOM_BOX, halfExtents=product_half_extents)
    prod_id = p.createMultiBody(baseMass=product_mass, baseCollisionShapeIndex=col_id, baseVisualShapeIndex=vis_id, basePosition=prod_start_pos, baseOrientation=product_start_orientation)
    products_data.append({
        "id": prod_id, "current_x": current_product_start_x, "current_y": product_start_y,
        "current_z": product_start_z, "orientation": product_start_orientation,
        "state": "ON_CONVEYOR", # ON_CONVEYOR, AT_INSPECTION, ACCEPTED_TO_END, REJECTED_ANIMATING, PROCESSED
        "color": prod_color, "batch_idx": batch_idx
    })
# products_data[0] is rearmost, products_data[num_products-1] is frontmost.

# --- Rejector Arm (Copied, assumed correct) ---
pusher_width_x_half = product_half_extents[0] * 1.2; pusher_depth_y_half = 0.025; pusher_height_z_half = product_half_extents[2]
pusher_half_extents = [pusher_width_x_half, pusher_depth_y_half, pusher_height_z_half]
pusher_color = [0.5, 0.5, 0.5, 1]; pusher_pos_x = inspection_x_limit
pusher_pos_y = conveyor_position[1] + conveyor_half_extents[1] + pusher_depth_y_half + 0.01 
pusher_pos_z = (conveyor_position[2] + conveyor_half_extents[2]) + product_half_extents[2] 
pusher_initial_position = [pusher_pos_x, pusher_pos_y, pusher_pos_z]; pusher_initial_orientation = p.getQuaternionFromEuler([0,0,0])
pusher_visual_shape_id = p.createVisualShape(shapeType=p.GEOM_BOX, halfExtents=pusher_half_extents, rgbaColor=pusher_color)
pusher_collision_shape_id = p.createCollisionShape(shapeType=p.GEOM_BOX, halfExtents=pusher_half_extents)
pusher_id = p.createMultiBody(baseMass=0,baseVisualShapeIndex=pusher_visual_shape_id,baseCollisionShapeIndex=pusher_collision_shape_id,basePosition=pusher_initial_position,baseOrientation=pusher_initial_orientation)
arm_radius = 0.02; arm_total_length = 0.15; arm_color = [0.3,0.3,0.3,1]
arm_pos_x = pusher_initial_position[0]; arm_pos_y = pusher_initial_position[1] + pusher_depth_y_half + (arm_total_length / 2.0) 
arm_pos_z = pusher_initial_position[2]; arm_initial_position = [arm_pos_x, arm_pos_y, arm_pos_z]; arm_initial_orientation = p.getQuaternionFromEuler([math.pi/2,0,0])
arm_visual_shape_id = p.createVisualShape(shapeType=p.GEOM_CYLINDER,radius=arm_radius,length=arm_total_length,rgbaColor=arm_color)
arm_collision_shape_id = p.createCollisionShape(shapeType=p.GEOM_CYLINDER,radius=arm_radius,height=arm_total_length)
arm_id = p.createMultiBody(baseMass=0,baseVisualShapeIndex=arm_visual_shape_id,baseCollisionShapeIndex=arm_collision_shape_id,basePosition=arm_initial_position,baseOrientation=arm_initial_orientation)
initial_arm_y_offset_from_pusher = arm_initial_position[1] - pusher_initial_position[1]

# --- Sensor & Camera Visuals (Copied, assumed correct) ---
sensor_radius, sensor_length, sensor_color = 0.03,0.05,[0.1,0.1,0.5,1]
sensor_pos_x, sensor_pos_y = inspection_x_limit, conveyor_position[1]-conveyor_half_extents[1]-sensor_length/2-0.3
sensor_pos_z = conveyor_position[2]+conveyor_half_extents[2] + 0.05; sensor_orientation = p.getQuaternionFromEuler([math.pi/2,0,0]) 
sensor_visual_id=p.createVisualShape(p.GEOM_CYLINDER,radius=sensor_radius,length=sensor_length,rgbaColor=sensor_color, visualFrameOrientation=p.getQuaternionFromEuler([0,0,math.pi/2])) 
p.createMultiBody(baseMass=0,baseVisualShapeIndex=sensor_visual_id,basePosition=[sensor_pos_x,sensor_pos_y,sensor_pos_z],baseOrientation=sensor_orientation)
cam_body_half_extents, cam_body_color = [0.04,0.06,0.02],[0.2,0.2,0.2,1]
cam_body_pos_x, cam_body_pos_y = inspection_x_limit, conveyor_position[1]
cam_body_pos_z = conveyor_position[2]+conveyor_half_extents[2]+0.25; cam_body_orientation=p.getQuaternionFromEuler([0,0,0])
cam_body_visual_id=p.createVisualShape(p.GEOM_BOX,halfExtents=cam_body_half_extents,rgbaColor=cam_body_color)
p.createMultiBody(baseMass=0,baseVisualShapeIndex=cam_body_visual_id,basePosition=[cam_body_pos_x,cam_body_pos_y,cam_body_pos_z],baseOrientation=cam_body_orientation)
cam_lens_radius, cam_lens_length, cam_lens_color = 0.025,0.04,[0.1,0.1,0.1,1]
cam_lens_pos_x, cam_lens_pos_y = cam_body_pos_x, cam_body_pos_y
cam_lens_pos_z = cam_body_pos_z - cam_body_half_extents[2]-(cam_lens_length/2.0); cam_lens_orientation=p.getQuaternionFromEuler([0,0,0])
cam_lens_visual_id=p.createVisualShape(p.GEOM_CYLINDER,radius=cam_lens_radius,length=cam_lens_length,rgbaColor=cam_lens_color)
p.createMultiBody(baseMass=0,baseVisualShapeIndex=cam_lens_visual_id,basePosition=[cam_lens_pos_x,cam_lens_pos_y,cam_lens_pos_z],baseOrientation=cam_lens_orientation)

# --- Camera View ---
p.resetDebugVisualizerCamera(cameraDistance=2.5, cameraYaw=50, cameraPitch=-30, cameraTargetPosition=[0.0,0,conveyor_height_above_ground])

# --- Simulation & Animation Parameters ---
product_speed = 0.2 
simulation_time_step = 1./240.
conveyor_is_running = True # Global state for conveyor movement

# Pusher
pusher_state = "RETRACTED" 
pusher_animation_speed = 0.3
product_target_y_rejected = -(conveyor_half_extents[1] + product_half_extents[1] * 2 + 0.25)
pusher_push_travel_distance = abs(product_target_y_rejected - 0) 
pusher_target_y_extended = pusher_initial_position[1] - pusher_push_travel_distance
pusher_retracted_y = pusher_initial_position[1]
pusher_extended_state_timer = 0
active_rejected_product_id = None 

# Inspection
product_at_inspection_idx = -1 
decision_pending = False # True when a product is AT_INSPECTION and waiting for key press
# INSPECTION_DELAY_STEPS is no longer needed if we wait for key press

try:
    for step in range(300000): 
        keys = p.getKeyboardEvents()
        
        # --- Determine Global Conveyor Running State ---
        conveyor_is_running = True # Assume running initially for this step

        if product_at_inspection_idx != -1 and products_data[product_at_inspection_idx]["state"] == "AT_INSPECTION":
            conveyor_is_running = False # Product is actively at inspection
        elif decision_pending: # Waiting for key press for a product that just arrived
            conveyor_is_running = False
        elif pusher_state != "RETRACTED": # Pusher is active
            conveyor_is_running = False
        else:
            # Check if the conveyor end is blocked by a non-moving processed/accepted item
            # This prevents further items from piling up if the end isn't clear.
            frontmost_product_overall_idx = -1
            for k_idx in range(num_products - 1, -1, -1):
                if products_data[k_idx]["state"] not in ["PROCESSED", "REJECTED_ANIMATING"]:
                    frontmost_product_overall_idx = k_idx
                    break
            
            if frontmost_product_overall_idx != -1:
                front_prod_data = products_data[frontmost_product_overall_idx]
                # If the very frontmost active product is already at conveyor_end_x and is ACCEPTED_TO_END (meaning it should stop there)
                if front_prod_data["state"] == "ACCEPTED_TO_END" and abs(front_prod_data["current_x"] - conveyor_end_x) < 0.01:
                    conveyor_is_running = False
                    # print(f"Debug: Conveyor stopped, product {frontmost_product_overall_idx} is at end.")


        # --- Product Movement on Conveyor ---
        if conveyor_is_running:
            # All products that are "ON_CONVEYOR" or "ACCEPTED_TO_END" (and not yet at final X) move by the same delta_x
            delta_x = product_speed * simulation_time_step

            for i in range(num_products): 
                prod_data = products_data[i]
                prod_id = prod_data["id"]

                if prod_data["state"] == "ON_CONVEYOR":
                    new_x = prod_data["current_x"] + delta_x
                    
                    # Determine which product is the current front-runner for inspection among ON_CONVEYOR ones
                    current_inspection_candidate_idx = -1
                    for k_idx in range(num_products - 1, -1, -1): # Frontmost to rearmost
                        if products_data[k_idx]["state"] == "ON_CONVEYOR":
                            current_inspection_candidate_idx = k_idx
                            break
                    
                    if i == current_inspection_candidate_idx and new_x >= inspection_x_limit:
                        new_x = inspection_x_limit 
                        prod_data["state"] = "AT_INSPECTION"
                        product_at_inspection_idx = i
                        decision_pending = True
                        print(f"Product {i} (Batch {prod_data['batch_idx']}) at inspection. Press '1' to ACCEPT, '0' to REJECT.")
                        # Conveyor will stop in the next iteration due to decision_pending or product_at_inspection_idx
                    
                    prod_data["current_x"] = new_x
                    p.resetBasePositionAndOrientation(prod_id, 
                                                      [new_x, prod_data["current_y"], prod_data["current_z"]], 
                                                      prod_data["orientation"])
                
                elif prod_data["state"] == "ACCEPTED_TO_END": 
                    new_x = prod_data["current_x"] + delta_x
                    if new_x >= conveyor_end_x:
                        new_x = conveyor_end_x
                        prod_data["state"] = "PROCESSED"
                        print(f"Product {i} (Batch {prod_data['batch_idx']}) ACCEPTED and reached end.")
                    
                    prod_data["current_x"] = new_x
                    p.resetBasePositionAndOrientation(prod_id, 
                                                      [new_x, prod_data["current_y"], prod_data["current_z"]], 
                                                      prod_data["orientation"])

        # --- Decision Making at Inspection (Key Press Based) ---
        if decision_pending and product_at_inspection_idx != -1:
            prod_inspect_data = products_data[product_at_inspection_idx]
            decision_made_this_step = False

            if ord('1') in keys and keys[ord('1')] & p.KEY_WAS_TRIGGERED: # ACCEPT
                print(f"Decision for Product {product_at_inspection_idx}: ACCEPTED (Key '1')")
                prod_inspect_data["state"] = "ACCEPTED_TO_END"
                product_at_inspection_idx = -1 # Free up inspection spot for conveyor run logic
                decision_made_this_step = True
            elif ord('0') in keys and keys[ord('0')] & p.KEY_WAS_TRIGGERED: # REJECT
                print(f"Decision for Product {product_at_inspection_idx}: REJECTED (Key '0')")
                prod_inspect_data["state"] = "REJECTED_ANIMATING"
                active_rejected_product_id = prod_inspect_data["id"]
                pusher_state = "EXTENDING"
                # product_at_inspection_idx remains for pusher logic until reject complete
                decision_made_this_step = True
            
            if decision_made_this_step:
                decision_pending = False
        
        # PUSHER ANIMATION
        if pusher_state != "RETRACTED" and active_rejected_product_id is not None:
            pusher_current_pos, pusher_current_orn = p.getBasePositionAndOrientation(pusher_id)
            arm_current_pos, arm_current_orn = p.getBasePositionAndOrientation(arm_id)
            prod_being_rejected_data = None; current_rejected_prod_idx = -1
            for idx, p_data_loop in enumerate(products_data):
                if p_data_loop["id"] == active_rejected_product_id:
                    prod_being_rejected_data = p_data_loop; current_rejected_prod_idx = idx; break
            
            if prod_being_rejected_data: 
                rejected_prod_orn_stored = prod_being_rejected_data["orientation"]
                rejected_prod_z_stored = prod_being_rejected_data["current_z"]
                if pusher_state == "EXTENDING":
                    new_pusher_y = pusher_current_pos[1] - pusher_animation_speed * simulation_time_step
                    pusher_contact_face_y = new_pusher_y - pusher_half_extents[1]
                    product_contact_face_y = prod_being_rejected_data["current_y"] + product_half_extents[1] 
                    product_is_being_pushed = pusher_contact_face_y <= product_contact_face_y
                    if new_pusher_y <= pusher_target_y_extended:
                        new_pusher_y = pusher_target_y_extended; pusher_state = "EXTENDED"
                    p.resetBasePositionAndOrientation(pusher_id, [pusher_current_pos[0], new_pusher_y, pusher_current_pos[2]], pusher_current_orn)
                    p.resetBasePositionAndOrientation(arm_id, [arm_current_pos[0], new_pusher_y + initial_arm_y_offset_from_pusher, arm_current_pos[2]], arm_current_orn)
                    if product_is_being_pushed:
                        prod_new_y = (new_pusher_y - pusher_half_extents[1]) - product_half_extents[1] 
                        prod_being_rejected_data["current_y"] = prod_new_y 
                        p.resetBasePositionAndOrientation(active_rejected_product_id, [prod_being_rejected_data["current_x"], prod_new_y, rejected_prod_z_stored], rejected_prod_orn_stored)
                elif pusher_state == "EXTENDED":
                    pusher_extended_state_timer += 1
                    if pusher_extended_state_timer >= int(240 * 0.5): 
                        pusher_state = "RETRACTING"; pusher_extended_state_timer = 0
                elif pusher_state == "RETRACTING":
                    new_pusher_y = pusher_current_pos[1] + pusher_animation_speed * simulation_time_step
                    if new_pusher_y >= pusher_retracted_y:
                        new_pusher_y = pusher_retracted_y; pusher_state = "RETRACTED"
                        print(f"Pusher retracted. Product {current_rejected_prod_idx} REJECTED & processed.")
                        prod_being_rejected_data["state"] = "PROCESSED" 
                        active_rejected_product_id = None
                        if product_at_inspection_idx == current_rejected_prod_idx: product_at_inspection_idx = -1
                    p.resetBasePositionAndOrientation(pusher_id, [pusher_current_pos[0], new_pusher_y, pusher_current_pos[2]], pusher_current_orn)
                    p.resetBasePositionAndOrientation(arm_id, [arm_current_pos[0], new_pusher_y + initial_arm_y_offset_from_pusher, arm_current_pos[2]], arm_current_orn)

        p.stepSimulation()
        time.sleep(simulation_time_step)

except KeyboardInterrupt:
    print("Simulation interrupted by user.")
finally:
    p.disconnect()
    print("Disconnected from PyBullet.")