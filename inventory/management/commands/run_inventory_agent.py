from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from inventory.models import InventoryItem
from core.models import AIConfiguration
import json
import logging

logger = logging.getLogger('inventory')

class Command(BaseCommand):
    help = 'Runs the Simulated Inventory Agent (rule-based, not actual AI)'
    
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.WARNING('NOTE: This is a SIMULATED agent, not real AI.'))
        self.stdout.write('For production, implement real demand forecasting with historical data.')
        self.stdout.write("Waking up Inventory Agent...")
        
        # 1. Check Low Stock Items
        low_items = InventoryItem.objects.filter(stock__lte=models.F('reorder_level'))
        if not low_items.exists():
            self.stdout.write("No low stock detected. Agent going back to sleep.")
            logger.info('Inventory agent: No low stock items found')
            return

        # 2. Rule-based restocking logic (not actual AI)
        purchase_orders = []
        for inv in low_items:
            po = {
                'item': inv.item.name,
                'current_stock': inv.stock,
                'reorder_level': inv.reorder_level,
                'order_qty': max(50, inv.reorder_level * 2),
                'reason': f"Stock is critically low ({inv.stock}). Rule-based restocking triggered."
            }
            purchase_orders.append(po)
            
            # Auto-replenish stock to simulate supplier fulfillment
            inv.stock += po['order_qty']
            inv.save()
            
        # 3. Generate Report
        report = {
            'timestamp': timezone.now().isoformat(),
            'orders': purchase_orders,
            'summary': f"Simulated restocking for {len(purchase_orders)} items. Stock has been auto-replenished."
        }
        
        # 4. Save to AI Configuration
        ai_config = AIConfiguration.get_solo()
        ai_config.last_inventory_order = json.dumps(report)
        ai_config.save()
        
        self.stdout.write(self.style.SUCCESS(f"Agent finished. Processed {len(purchase_orders)} items."))
