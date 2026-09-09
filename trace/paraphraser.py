"""
Blinded Paraphrase Suite Generator (Pilot-2 Experiment 1)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Generates naturalistic, blinded procurement intents across 4 distinct semantic clusters:
1. Routine regional warehouse inventory transfer (East/West hubs)
2. Expedited critical stock emergency orders (High-priority, budget ceiling checks)
3. Specialized high-volume component procurement (Strict MOQ >= 10, vendor codes)
4. Routine multi-item stock depot rebalancing
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class BlindedTask:
    task_id: str
    semantic_cluster: str
    intent_family: str
    user_intent: str
    split: str
    target_constraints: List[str]

def generate_pilot2_blinded_tasks() -> List[BlindedTask]:
    tasks = []

    c1_templates = [
        ('family_a', 'Please create a replenishment order for 50 units of standard electronic components routed to our east coast depot.', 'train'),
        ('family_a', 'We need to restock 40 widgets for the eastern distribution hub under our primary supplier contract.', 'train'),
        ('family_a', 'Process an inventory restock of 60 parts for the western logistics center from Texas Semi.', 'train'),
        ('family_a', 'Initiate a regular stock delivery of 45 units to our US-East facility.', 'train'),
        ('family_a', 'Submit a standard order for thirty assemblies heading to the West warehouse.', 'train'),
        ('family_a', 'Procure 55 items from Texas Semi for delivery at the eastern regional hub.', 'train'),
        ('family_b', 'Low stock detected at the East terminal; order 70 additional units under routine terms.', 'train'),
        ('family_b', 'Send fifty replacement microcontrollers to our Atlantic logistics dock.', 'train'),
        ('family_b', 'Issue a purchase requisition for 35 units to replenish our western regional storage.', 'train'),
        ('family_b', 'East coast facility is running low on stock; please order forty standard units.', 'train'),
        ('family_b', 'Refill inventory at the Pacific depot with sixty units of part SKU-10005.', 'train'),
        ('family_b', 'Place our monthly scheduled order of 50 units for the eastern regional center.', 'train'),
        ('family_c', 'Restock our east depot with 50 units using our standard vendor agreement.', 'test'),
        ('family_c', 'Have procurement route forty units of SKU-10008 to the eastern facility.', 'test'),
        ('family_c', 'We require thirty additional parts delivered to the western depot by next cycle.', 'test'),
        ('family_c', 'Supply chain notice: dispatch 45 units to our US East regional distribution site.', 'test'),
        ('family_c', 'Send forty inventory pieces to our western operations terminal.', 'test'),
        ('family_c', 'Order 50 replacement modules for delivery to our east coast branch.', 'test'),
        ('family_c', 'Prepare standard shipment of 60 items to the west coast facility.', 'test'),
        ('family_c', 'Execute routine replenishment: 40 units routed to east depot.', 'test'),
    ]

    for idx, (fam, intent, split) in enumerate(c1_templates, 1):
        tasks.append(BlindedTask(
            task_id=f'BLIND-C1-{idx:03d}',
            semantic_cluster='routine_regional_replenish',
            intent_family=fam,
            user_intent=intent,
            split=split,
            target_constraints=['warehouse_code.enum', 'authorized_by.pattern']
        ))

    c2_templates = [
        ('family_a', 'Urgent request: rush order 25 vital components to East hub with maximum authorization.', 'train'),
        ('family_a', 'Production line halted! Immediately dispatch 20 sensors under critical priority.', 'train'),
        ('family_a', 'Emergency stockout alert: expedite 15 control modules to West terminal right away.', 'train'),
        ('family_a', 'Fast-track purchase order for 30 power units needed immediately on site.', 'train'),
        ('family_a', 'Critical priority replenishment of 25 replacement boards to the East depot.', 'train'),
        ('family_a', 'Rush delivery required: procure 20 semiconductor parts under expedited handling.', 'train'),
        ('family_b', 'Priority dispatch: route 15 emergency backup units to the western warehouse immediately.', 'train'),
        ('family_b', 'Critical supply disruption: purchase 25 emergency parts with priority shipping.', 'train'),
        ('family_b', 'Urgent dispatch needed: order 30 items immediately under critical terms.', 'train'),
        ('family_b', 'Expedite delivery of 20 critical repair units to our East logistics terminal.', 'train'),
        ('family_b', 'Production critical: secure 25 modules right away with top priority routing.', 'train'),
        ('family_b', 'Emergency reorder: dispatch 15 units of SKU-10012 to West coast without delay.', 'train'),
        ('family_c', 'Top priority: rush 20 units to our eastern warehouse to avoid assembly shutdown.', 'test'),
        ('family_c', 'Immediate replenishment needed: expedite 25 units for critical East terminal operations.', 'test'),
        ('family_c', 'Factory emergency: order 15 replacement components under critical expedition terms.', 'test'),
        ('family_c', 'Urgent order: send 30 essential parts to our West facility under highest priority.', 'test'),
        ('family_c', 'Rush shipment authorized: procure 20 units for immediate delivery to East depot.', 'test'),
        ('family_c', 'Emergency ticket #409: expedite purchase of 25 items to prevent line stoppage.', 'test'),
        ('family_c', 'High-severity stock failure: dispatch 15 urgent units to West regional hub.', 'test'),
        ('family_c', 'Critical stock alert: place urgent purchase for 20 modules heading to East dock.', 'test'),
    ]

    for idx, (fam, intent, split) in enumerate(c2_templates, 1):
        tasks.append(BlindedTask(
            task_id=f'BLIND-C2-{idx:03d}',
            semantic_cluster='expedited_emergency_order',
            intent_family=fam,
            user_intent=intent,
            split=split,
            target_constraints=['order_priority.enum', 'total_budget_limit.maximum']
        ))

    c3_templates = [
        ('family_a', 'Contract purchase: reorder bulk supply of raw microchips from our certified semiconductor vendor.', 'train'),
        ('family_a', 'Procure bulk batch of 100 microcontrollers honoring supplier volume tier agreements.', 'train'),
        ('family_a', 'Order 120 precision resistors meeting vendor bulk minimums from certified supplier.', 'train'),
        ('family_a', 'Submit volume purchase order for 80 units adhering to Texas Semi contract rules.', 'train'),
        ('family_a', 'Replenish 150 structural brackets from primary manufacturer under wholesale pricing.', 'train'),
        ('family_a', 'Wholesale acquisition: order 90 sensor arrays from contracted supplier.', 'train'),
        ('family_b', 'Purchase order for 110 items meeting mandatory manufacturer batch packaging.', 'train'),
        ('family_b', 'Volume restock: order 100 units of SKU-10020 subject to certified vendor ID validation.', 'train'),
        ('family_b', 'Procure 85 industrial relays from supplier Texas Semi under agreed bulk MOQ terms.', 'train'),
        ('family_b', 'Bulk procurement: issue order for 130 components meeting commercial vendor constraints.', 'train'),
        ('family_b', 'Wholesale restocking: buy 95 modules from qualified supplier under volume contract.', 'train'),
        ('family_b', 'Order 105 specialty units honoring vendor certification and packaging thresholds.', 'train'),
        ('family_c', 'Execute bulk order of 100 items from contracted vendor meeting minimum batch requirements.', 'test'),
        ('family_c', 'Wholesale replenishment: procure 120 units from certified supplier Texas Semi.', 'test'),
        ('family_c', 'Contract requisition for 90 parts honoring supplier minimum order volume standards.', 'test'),
        ('family_c', 'Place bulk procurement request for 110 units from approved semiconductor supplier.', 'test'),
        ('family_c', 'Order 100 replacement assemblies meeting certified vendor procurement specifications.', 'test'),
        ('family_c', 'Restock 80 specialized items ensuring manufacturer MOQ thresholds are satisfied.', 'test'),
        ('family_c', 'Commercial wholesale order: 125 units from primary contracted vendor.', 'test'),
        ('family_c', 'Procure 95 batch components from certified supplier following volume agreements.', 'test'),
    ]

    for idx, (fam, intent, split) in enumerate(c3_templates, 1):
        tasks.append(BlindedTask(
            task_id=f'BLIND-C3-{idx:03d}',
            semantic_cluster='specialized_bulk_procurement',
            intent_family=fam,
            user_intent=intent,
            split=split,
            target_constraints=['items.quantity.minimum', 'supplier_id.pattern']
        ))

    c4_templates = [
        ('family_a', 'Rebalance multi-item inventory: order 30 units of SKU-10001 and 40 units of SKU-10002.', 'train'),
        ('family_a', 'Depot rebalance: order 25 units of primary SKU and 35 units of secondary SKU for East facility.', 'train'),
        ('family_a', 'Multi-line purchase order: allocate 20 units of part A and 30 units of part B.', 'train'),
        ('family_a', 'Stock level alignment: reorder 40 units across multiple catalog items for West depot.', 'train'),
        ('family_a', 'Composite replenishment order containing two distinct component lines for distribution.', 'train'),
        ('family_a', 'Consolidated purchase: combine 30 units of item 1 and 25 units of item 2 in one order.', 'train'),
        ('family_b', 'Create multi-sku procurement order covering dual part requirements for East hub.', 'train'),
        ('family_b', 'Bundle restock: order 35 units of SKU-10004 alongside 25 units of SKU-10005.', 'train'),
        ('family_b', 'Joint shipment request: replenish 20 units of line item 1 and 30 units of line item 2.', 'train'),
        ('family_b', 'Order two distinct item lines for depot inventory balance under standard terms.', 'train'),
        ('family_b', 'Composite parts requisition: restock 25 units of first SKU and 40 units of second SKU.', 'train'),
        ('family_b', 'Multi-item supply dispatch: bundle 30 units of part A and 30 units of part B.', 'train'),
        ('family_c', 'Issue dual-line replenishment order for 25 units of SKU-10006 and 35 units of SKU-10007.', 'test'),
        ('family_c', 'Consolidate two product lines into one replenishment order for the eastern depot.', 'test'),
        ('family_c', 'Multi-item stock order: acquire 30 units of component 1 and 20 units of component 2.', 'test'),
        ('family_c', 'Rebalance regional storage with a combined order of two separate catalog parts.', 'test'),
        ('family_c', 'Dual-item requisition: place order for 25 units of SKU-10008 and 30 units of SKU-10009.', 'test'),
        ('family_c', 'Bundle replenishment request across multiple stock keeping units for West terminal.', 'test'),
        ('family_c', 'Assemble combined purchase order covering two inventory lines for East hub.', 'test'),
        ('family_c', 'Multi-part dispatch: order 35 units of first item and 25 units of second item.', 'test'),
    ]

    for idx, (fam, intent, split) in enumerate(c4_templates, 1):
        tasks.append(BlindedTask(
            task_id=f'BLIND-C4-{idx:03d}',
            semantic_cluster='multi_item_depot_rebalance',
            intent_family=fam,
            user_intent=intent,
            split=split,
            target_constraints=['items.minItems', 'items.sku.pattern', 'items.required']
        ))

    return tasks
