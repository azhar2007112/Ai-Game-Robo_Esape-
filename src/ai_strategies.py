from queue import PriorityQueue
import random

def a_star(start, goal, board):
    dirs = [(1,0),(-1,0),(0,1),(0,-1)]
    open_set = PriorityQueue()
    open_set.put((0,start))
    came_from = {}
    g_score = {start:0}

    while not open_set.empty():
        _, current = open_set.get()
        if current == goal:
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.reverse()
            return path
        for dx, dy in dirs:
            neighbor = (current[0]+dx, current[1]+dy)
            if 0 <= neighbor[0] < board.size and 0 <= neighbor[1] < board.size:
                if board.grid[neighbor[0]][neighbor[1]] == "X": continue
                tentative = g_score[current] + 1
                if neighbor not in g_score or tentative < g_score[neighbor]:
                    g_score[neighbor] = tentative
                    f = tentative + abs(neighbor[0]-goal[0]) + abs(neighbor[1]-goal[1])
                    open_set.put((f, neighbor))
                    came_from[neighbor] = current
    return []

# ---------- Minimax with Alpha-Beta (hard mode) ----------
def _evaluate_state(ai_pos, ai_health, player_pos, player_health):
    dist = abs(ai_pos[0]-player_pos[0]) + abs(ai_pos[1]-player_pos[1])
    return (ai_health - player_health) - 0.5*dist

def _neighbors(pos, board):
    for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
        nx,ny = pos[0]+dx, pos[1]+dy
        if 0<=nx<board.size and 0<=ny<board.size and board.grid[nx][ny] != "X":
            yield (nx,ny)

def _minimax(ai_pos, ai_health, player_pos, player_health, board, depth, alpha, beta, maximizing):
    if depth==0 or ai_health<=0 or player_health<=0:
        return _evaluate_state(ai_pos, ai_health, player_pos, player_health), None
    if maximizing:
        best = -10**9; best_action=None
        actions=[]
        actions.append(("stay", ai_pos))
        for n in _neighbors(ai_pos, board): actions.append(("move", n))
        if abs(ai_pos[0]-player_pos[0])+abs(ai_pos[1]-player_pos[1])<=2:
            actions.append(("melee", ai_pos))
        actions.append(("shoot", ai_pos))
        for atype,npos in actions:
            nai_pos, nai_health, npl_pos, npl_health = ai_pos, ai_health, player_pos, player_health
            if atype=="move":
                nai_pos = npos
            elif atype=="melee":
                npl_health = max(0, npl_health-10)
            # shoot is delayed; heuristic benefit applied in evaluation via distance
            val,_ = _minimax(nai_pos, nai_health, npl_pos, npl_health, board, depth-1, alpha, beta, False)
            if atype=="shoot":
                val += 2  # slight bias to use ranged when far
            if val>best:
                best=val; best_action=(atype,npos)
            alpha = max(alpha, best)
            if beta<=alpha: break
        return best, best_action
    else:
        best = 10**9; best_action=None
        actions=[]
        actions.append(("stay", player_pos))
        for n in _neighbors(player_pos, board): actions.append(("move", n))
        if abs(ai_pos[0]-player_pos[0])+abs(ai_pos[1]-player_pos[1])<=2:
            actions.append(("melee", player_pos))
        for atype,npos in actions:
            nai_pos, nai_health, npl_pos, npl_health = ai_pos, ai_health, player_pos, player_health
            if atype=="move":
                npl_pos = npos
            elif atype=="melee":
                nai_health = max(0, nai_health-10)
            val,_ = _minimax(nai_pos, nai_health, npl_pos, npl_health, board, depth-1, alpha, beta, True)
            if val<best:
                best=val; best_action=(atype,npos)
            beta = min(beta, best)
            if beta<=alpha: break
        return best, best_action

def _minimax_eval(ai, player, board):
    return (ai.health - player.health) + (ai.score - player.score) * 0.5 - ai.distance(player)

def ai_decision(ai, player, board, level='easy'):
    # Stun handling: if stunned, skip action this turn
    if hasattr(ai, 'stunned_turns') and ai.stunned_turns and ai.stunned_turns > 0:
        ai.stunned_turns -= 1
        return
    dist = ai.distance(player)
    health_low = max(0, min(1, (50 - ai.health)/50))
    health_high = max(0, min(1, (ai.health-50)/50))
    dist_close = max(0, min(1, (2 - dist)/2))
    dist_far = max(0, min(1, (dist-2)/5))

    # Normalize decision so either agent plays the same logic
    if getattr(ai, 'personality', 'Balanced') == 'Aggressive':
        score_attack = dist_close * health_high + 0.3
        score_retreat = health_low
        score_gather = dist_far * 0.5
    elif getattr(ai, 'personality', 'Balanced') == 'Defensive':
        score_attack = dist_close * health_high * 0.5
        score_retreat = health_low + 0.3
        score_gather = dist_far
    else:
        score_attack = dist_close * health_high
        score_retreat = health_low
        score_gather = dist_far * 0.7

    # Difficulty scaling
    if level == 'easy':
        score_attack *= 0.7
        score_gather *= 0.9
    elif level == 'medium':
        score_attack *= 1.0
        score_gather *= 1.1
    elif level == 'hard':
        score_attack *= 1.3
        score_gather *= 1.3

    # EASY: fuzzy with more weight on resource than goal; melee if near
    if level == 'easy':
        if dist <= 2:
            ai.attack(player); return
        goal = getattr(board, 'end_ai', (0,0))
        if board.resources:
            nearest = min(board.resources, key=lambda r: abs(ai.pos[0]-r[0])+abs(ai.pos[1]-r[1]))
            d_res = abs(ai.pos[0]-nearest[0])+abs(ai.pos[1]-nearest[1])
        else:
            nearest = None; d_res = 99
        d_end = abs(ai.pos[0]-goal[0])+abs(ai.pos[1]-goal[1])
        near_resource = max(0, min(1, (8 - d_res)/8))
        far_from_end = max(0, min(1, (d_end - 6)/10))
        # resource weighted higher
        score_gather_fuzzy = 0.7*near_resource + 0.3*far_from_end
        score_goal_fuzzy = 0.4*(1-near_resource) + 0.6*(1-far_from_end)
        if nearest and score_gather_fuzzy >= score_goal_fuzzy:
            path = a_star(ai.pos, nearest, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        path = a_star(ai.pos, goal, board)
        if path:
            step = path[0]
            ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        dx,dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        ai.move(dx,dy,board); return

    # MEDIUM: fuzzy decide gather vs head to end; goal has more weight; still melee if in range
    if level == 'medium':
        if dist <= 2:
            ai.attack(player); return
        goal = getattr(board, 'end_ai', (0,0))
        # fuzzy inputs: distance to nearest resource, distance to end
        if board.resources:
            nearest = min(board.resources, key=lambda r: abs(ai.pos[0]-r[0])+abs(ai.pos[1]-r[1]))
            d_res = abs(ai.pos[0]-nearest[0])+abs(ai.pos[1]-nearest[1])
        else:
            nearest = None; d_res = 99
        d_end = abs(ai.pos[0]-goal[0])+abs(ai.pos[1]-goal[1])
        near_resource = max(0, min(1, (6 - d_res)/6))
        far_from_end = max(0, min(1, (d_end - 4)/8))
        score_gather_fuzzy = 0.4*near_resource + 0.6*far_from_end
        score_goal_fuzzy = 0.75*(1-near_resource) + 0.25*(1-far_from_end)
        if score_goal_fuzzy > score_gather_fuzzy or not nearest:
            path = a_star(ai.pos, goal, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        else:
            path = a_star(ai.pos, nearest, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        dx,dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        ai.move(dx,dy,board); return

    # HARD: prioritize Attack > Goal > Resource
    if level == 'hard':
        # If in melee range, attack
        if dist <= 2:
            ai.attack(player); return
        goal = getattr(board, 'end_ai', (0,0))
        if board.resources:
            nearest = min(board.resources, key=lambda r: abs(ai.pos[0]-r[0])+abs(ai.pos[1]-r[1]))
            d_res = abs(ai.pos[0]-nearest[0])+abs(ai.pos[1]-nearest[1])
        else:
            nearest = None; d_res = 99
        d_end = abs(ai.pos[0]-goal[0])+abs(ai.pos[1]-goal[1])
        near_resource = max(0, min(1, (6 - d_res)/6))
        far_from_end = max(0, min(1, (d_end - 4)/8))
        # Tune desires so AI doesn't end too fast: require stronger desire to attack, otherwise progress to goal
        # Reduce attack desire if ranged is on cooldown to avoid confusing spam
        attack_desire = 0.7*dist_far + 0.3*health_high
        if getattr(ai, 'ranged_cooldown', 0) > 0:
            attack_desire *= 0.6
        goal_desire = 0.7*(1-far_from_end)
        gather_desire = 0.3*near_resource
        if attack_desire >= max(goal_desire, gather_desire):
            # prefer attack; if ranged on cooldown, move toward player aggressively instead of idling
            if getattr(ai, 'ranged_cooldown', 0) == 0:
                ai.pending_ranged = {'target_pos': player.pos, 'turns': 1}
                ai.ranged_cooldown = 3
                return
            else:
                ai.ranged_cooldown -= 1
                # move toward player
                path = a_star(ai.pos, player.pos, board)
                if path:
                    step = path[0]
                    ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board)
                return
        if goal_desire >= gather_desire:
            path = a_star(ai.pos, goal, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        if nearest:
            path = a_star(ai.pos, nearest, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board); return
        dx,dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
        ai.move(dx,dy,board); return

    actions = {'attack': score_attack, 'retreat': score_retreat, 'gather': score_gather}
    action = max(actions, key=actions.get)

    if action == 'retreat':
        moves = [(1,0),(-1,0),(0,1),(0,-1)]
        random.shuffle(moves)
        for dx,dy in moves:
            nx, ny = ai.pos[0]+dx, ai.pos[1]+dy
            if 0 <= nx < board.size and 0 <= ny < board.size and board.grid[nx][ny] != "X":
                ai.move(dx, dy, board)
                return
    elif action == 'attack':
        # Attack cooldown handling by difficulty
        cd = getattr(ai, 'attack_cooldown', 0)
        if cd > 0:
            ai.attack_cooldown = cd - 1
            # fallback move toward player slightly using A*
            path = a_star(ai.pos, player.pos, board)
            if path:
                step = path[0]
                ai.move(step[0]-ai.pos[0], step[1]-ai.pos[1], board)
            return
        melee_range = 1 if level=='easy' else 2
        if level in ('easy','medium') and dist <= melee_range:
            ai.attack(player)
            ai.attack_cooldown = 2 if level=='easy' else 1
            return
        if level == 'hard':
            # If in melee range, prioritize immediate melee
            if dist <= 2:
                ai.attack(player)
                return
            # Use minimax to choose action
            _, best = _minimax(ai.pos, ai.health, player.pos, player.health, board, depth=2, alpha=-10**9, beta=10**9, maximizing=True)
            if best:
                atype, npos = best
                if atype=='melee' and dist<=2:
                    ai.attack(player); return
                if atype=='move' and npos:
                    dx,dy = npos[0]-ai.pos[0], npos[1]-ai.pos[1]
                    ai.move(dx,dy,board); return
                if atype=='shoot' and dist>2:
                    ai.pending_ranged = {'target_pos': player.pos, 'turns': 1}; return
            # fallback
            if dist>2:
                ai.pending_ranged = {'target_pos': player.pos, 'turns': 1}; return
            ai.attack(player); return
    elif action == 'gather' and board.resources:
        target = min(board.resources, key=lambda r: abs(ai.pos[0]-r[0])+abs(ai.pos[1]-r[1]))
        path = a_star(ai.pos, target, board)
        if path:
            next_step = path[0]
            dx, dy = next_step[0]-ai.pos[0], next_step[1]-ai.pos[1]
            ai.move(dx, dy, board)
            return
        # Medium: occasionally fire ranged to harass when far
        if level=='medium' and dist>2 and random.random()<0.4:
            ai.pending_ranged = {'target_pos': player.pos, 'turns': 1}
            return
    dx,dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
    ai.move(dx,dy,board)



def predict_next_move(player, board):
    """Predict player's next tile based on last move or nearest resource."""
    # Default: stay in place
    predicted = player.pos  

    # If player just moved recently, extrapolate direction
    if hasattr(player, "last_pos"):
        dx = player.pos[0] - player.last_pos[0]
        dy = player.pos[1] - player.last_pos[1]
        predicted = (player.pos[0] + dx, player.pos[1] + dy)
        # keep inside bounds
        if not (0 <= predicted[0] < board.size and 0 <= predicted[1] < board.size):
            predicted = player.pos

    # Otherwise, bias prediction toward nearest resource
    elif board.resources:
        closest = min(board.resources.keys(),
                      key=lambda r: abs(r[0]-player.pos[0]) + abs(r[1]-player.pos[1]))
        dx = (closest[0] - player.pos[0])
        dy = (closest[1] - player.pos[1])
        step = (player.pos[0] + (1 if dx>0 else -1 if dx<0 else 0),
                player.pos[1] + (1 if dy>0 else -1 if dy<0 else 0))
        predicted = step

    return predicted




def ai_vs_ai_decision(ai, opponent, board, level='medium'):
    """Smart AI for AI vs AI mode with goals prioritized over endless melee."""

    # Handle stun
    if hasattr(ai, 'stunned_turns') and ai.stunned_turns:
        ai.stunned_turns -= 1
        return

    # --- AUTO-GOAL DISCOVERY (important!) ---
    # If this AI doesn't have an explicit goal, pick the farthest of the two corners.
    # This guarantees: AI at (0,0) will choose (n-1,n-1), and vice versa.
    if not hasattr(ai, 'goal') or ai.goal is None:
        n = board.size
        corners = [(0, 0), (n-1, n-1)]
        ai.goal = max(corners, key=lambda c: abs(ai.pos[0]-c[0]) + abs(ai.pos[1]-c[1]))

    goal = ai.goal

    dist = ai.distance(opponent)
    melee_range = 2
    melee_damage = getattr(ai, 'melee_damage', 10)


    # Track progress and last moves
    cur_goal_dist = abs(ai.pos[0]-goal[0]) + abs(ai.pos[1]-goal[1])
    if not hasattr(ai, '_last_goal_dist'):
        ai._last_goal_dist = cur_goal_dist
    if not hasattr(ai, '_no_progress_turns'):
        ai._no_progress_turns = 0
    if not hasattr(ai, '_last_pos'):
        ai._last_pos = None
    if not hasattr(ai, '_attack_cooldown'):
        ai._attack_cooldown = 0

    if cur_goal_dist >= ai._last_goal_dist:
        ai._no_progress_turns += 1
    else:
        ai._no_progress_turns = 0

    # 1) Lethal strike (always finish enemy if possible)
    if dist <= melee_range and opponent.health <= melee_damage:
        ai.attack(opponent)
        ai._attack_cooldown = 1
        ai._last_goal_dist = cur_goal_dist
        ai._last_pos = ai.pos
        return

    # 2) If in melee range but we already attacked last turn → move instead
    if dist <= melee_range:
        if ai._attack_cooldown > 0:
            ai._attack_cooldown -= 1
            path = a_star(ai.pos, goal, board)
            if path:
                next_step = path[0]
                # ✅ avoid oscillation: don’t step back into last_pos
                if ai._last_pos and next_step == ai._last_pos:
                    # try alternate directions
                    moves = [(1,0),(-1,0),(0,1),(0,-1)]
                    random.shuffle(moves)
                    moved = False
                    for dx,dy in moves:
                        nx, ny = ai.pos[0]+dx, ai.pos[1]+dy
                        if (0 <= nx < board.size and 0 <= ny < board.size 
                            and board.grid[nx][ny] != "X" 
                            and (nx,ny) != ai._last_pos):
                            ai.move(dx, dy, board)
                            moved = True
                            break
                    if not moved:  # fallback if stuck
                        dx, dy = random.choice(moves)
                        ai.move(dx, dy, board)
                else:
                    dx, dy = next_step[0]-ai.pos[0], next_step[1]-ai.pos[1]
                    ai.move(dx, dy, board)
                ai._last_goal_dist = abs(ai.pos[0]-goal[0]) + abs(ai.pos[1]-goal[1])
                ai._last_pos = ai.pos
                return
        else:
            # Attack once, then set cooldown so we won’t repeat
            ai.attack(opponent)
            ai._attack_cooldown = 1
            ai._last_goal_dist = cur_goal_dist
            ai._last_pos = ai.pos
            return

    # 3) Ranged harassment
    if 3 <= dist <= 5 and getattr(ai, 'ranged_cooldown', 0) == 0:
        ai.pending_ranged = {'target_pos': opponent.pos, 'turns': 1}
        ai.ranged_cooldown = 3
        ai._last_goal_dist = cur_goal_dist
        ai._last_pos = ai.pos
        return
    else:
        if getattr(ai, 'ranged_cooldown', 0) > 0:
            ai.ranged_cooldown -= 1

    # 4) Path to goal
    chosen_step = None
    pg = a_star(ai.pos, goal, board)
    if pg:
        chosen_step = pg[0]

    # Opportunistic resource
    if board.resources:
        nearest = min(board.resources, key=lambda r: abs(ai.pos[0]-r[0]) + abs(ai.pos[1]-r[1]))
        pr = a_star(ai.pos, nearest, board)
        if pr:
            step_r = pr[0]
            if (chosen_step is None or
                (abs(step_r[0]-goal[0]) + abs(step_r[1]-goal[1])
                 <= abs(chosen_step[0]-goal[0]) + abs(chosen_step[1]-goal[1]))):
                chosen_step = step_r

    # 5) Execute movement (anti-oscillation here too)
    if chosen_step:
        if ai._last_pos and chosen_step == ai._last_pos:
            # choose alternative direction
            moves = [(1,0),(-1,0),(0,1),(0,-1)]
            random.shuffle(moves)
            for dx,dy in moves:
                nx, ny = ai.pos[0]+dx, ai.pos[1]+dy
                if (0 <= nx < board.size and 0 <= ny < board.size 
                    and board.grid[nx][ny] != "X" 
                    and (nx,ny) != ai._last_pos):
                    ai.move(dx, dy, board)
                    ai._last_pos = ai.pos
                    ai._last_goal_dist = abs(ai.pos[0]-goal[0]) + abs(ai.pos[1]-goal[1])
                    return
            # fallback
            dx, dy = random.choice(moves)
            ai.move(dx, dy, board)
        else:
            dx, dy = chosen_step[0]-ai.pos[0], chosen_step[1]-ai.pos[1]
            ai.move(dx, dy, board)
        ai._last_goal_dist = abs(ai.pos[0]-goal[0]) + abs(ai.pos[1]-goal[1])
        ai._last_pos = ai.pos
        return

    # 6) Fallback random move
    dx, dy = random.choice([(1,0),(-1,0),(0,1),(0,-1)])
    ai.move(dx, dy, board)
    ai._last_goal_dist = cur_goal_dist
    ai._last_pos = ai.pos
